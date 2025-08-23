import functools
import gc
import logging
import os
import platform
import shutil
import sys
import time
import traceback
from collections.abc import Callable, Generator
from contextlib import nullcontext, suppress
from inspect import signature
from pathlib import Path
from typing import Any, Optional, cast, overload

import torch
import torch.distributed as dist
from torch import nn
from torch.nn.parallel import DistributedDataParallel as DDP_th
from torch.utils.data import DataLoader

from trainer._types import Callback, LossDict, LRScheduler, ValueListDict
from trainer.callbacks import TrainerCallback
from trainer.config import TrainerArgs, TrainerConfig
from trainer.generic_utils import (
    KeepAverage,
    count_parameters,
    get_experiment_folder_path,
    get_git_branch,
    is_pytorch_at_least_2_3,
    is_pytorch_at_least_2_4,
    iter_value_list_dict,
    map_value_list_dict,
    remove_experiment_folder,
    set_partial_state_dict,
    to_cuda,
)
from trainer.io import (
    copy_model_files,
    get_last_checkpoint,
    load_fsspec,
    save_best_model,
    save_checkpoint,
)
from trainer.logging import ConsoleLogger, DummyLogger, logger_factory
from trainer.logging.base_dash_logger import BaseDashboardLogger
from trainer.model import TrainerModel
from trainer.trainer_utils import (
    get_optimizer,
    get_scheduler,
    print_training_env,
    setup_torch_training_env,
)
from trainer.utils.cuda_memory import cuda_meminfo, should_reduce_batch_size
from trainer.utils.distributed import (
    get_rank,
    init_distributed,
    rank_zero_logger_info,
    rank_zero_only,
)

logger = logging.getLogger("trainer")

if is_pytorch_at_least_2_3():
    GradScaler = functools.partial(torch.GradScaler, device="cuda")
else:
    GradScaler = torch.cuda.amp.GradScaler  # type: ignore[assignment]


class Trainer:
    def __init__(  # pylint: disable=dangerous-default-value
        self,
        args: TrainerArgs,
        config: TrainerConfig,
        output_path: str | os.PathLike[Any] | None = None,
        *,
        c_logger: ConsoleLogger | None = None,
        dashboard_logger: BaseDashboardLogger | None = None,
        model: TrainerModel | None = None,
        get_model: Callable[..., TrainerModel] | None = None,
        get_data_samples: Callable[..., list[Any]] | None = None,
        train_samples: list[Any] | None = None,
        eval_samples: list[Any] | None = None,
        test_samples: list[Any] | None = None,
        train_loader: DataLoader[Any] | None = None,
        eval_loader: DataLoader[Any] | None = None,
        training_assets: dict[str, Any] | None = None,
        parse_command_line_args: bool = True,
        callbacks: dict[str, Callback] | None = None,
        gpu: int | None = None,
    ) -> None:
        """Simple yet powerful 🐸💬 TTS trainer for PyTorch.

        It can train all the available `tts` and `vocoder` models or easily be customized.

        Notes:
            Supports Automatic Mixed Precision training using PyTorch's native `amp` module.

        Args:
            args (TrainerArgs): Training arguments parsed either from console by `argparse` or `TrainerArgs`
                config object.

            config (TrainerConfig): Model config object. It includes all the values necessary for initializing, training, evaluating
                and testing the model.

            output_path (str or Path, optional): Path to the output training folder. All
                the files are saved under this path. Uses value from config if None.

            c_logger (ConsoleLogger, optional): Console logger for printing training status. If not provided, the default
                console logger is used. Defaults to None.

            dashboard_logger Union[TensorboardLogger, WandbLogger]: Dashboard logger. If not provided, the tensorboard logger is used.
                Defaults to None.

            model (TrainerModel, optional): Initialized and ready-to-train model. If it is not defined, `Trainer`
                initializes a model from the provided config. Defaults to None.

            get_model (Callable):
                A function that returns a model. It is used to initialize the model when `model` is not provided.
                It either takes the config as the only argument or does not take any argument.
                Defaults to None

            get_data_samples (Callable):
                A function that returns a list of training and evaluation samples. Used if `train_samples` and
                `eval_samples` are None. Defaults to None.

            train_samples (List):
                A list of training samples used by the model's `get_train_data_loader` to init the `dataset` and the
                `data_loader`. Defaults to None.

            eval_samples (List):
                A list of evaluation samples used by the model's `get_eval_data_loader` to init the `dataset` and the
                `data_loader`. Defaults to None.

            train_loader (DataLoader):
                A pytorch data loader object for training epochs. Leave as None if you want it to be made during training. Defaults to None.

            eval_loader (DataLoader):
                A pytorch data loader object for evaluation epochs. Leave as None to be generated during training. Defaults to None.

            test_samples (List):
                A list of test samples used by the model's `get_test_data_loader` to init the `dataset` and the
                `data_loader`. If None, the ```model.test_run()``` is expected to load the data. Defaults to None.

            training_assets (Dict):
                A dictionary of assets to be used at training and passed to the model's ```train_log(), eval_log(), get_data_loader()```
                during training. It can include  `AudioProcessor` or/and `Tokenizer`. Defaults to {}.

            parse_command_line_args (bool):
                If true, parse command-line arguments and update `TrainerArgs` and model `config` values. Set it
                to false if you parse the arguments yourself. Defaults to True.

            callbacks (Dict[str, Callable]):
                A dictionary of callbacks to be used during training. The keys are the callback names and the values

            gpu (int):
                GPU ID to use for training If "CUDA_VISIBLE_DEVICES" is not set. Defaults to None.

        Example::

            Running trainer with a model.

            >>> args = TrainerArgs(...)
            >>> config = ModelConfig(...)
            >>> model = Model(config)
            >>> trainer = Trainer(args, config, model=model)
            >>> trainer.fit()

        TODO:
                - Wrap model for not calling .module in DDP.
                - Deepspeed integration
                - Profiler integration.
                - Overfitting to a batch.
                - TPU training
        """
        if training_assets is None:
            training_assets = {}
        if callbacks is None:
            callbacks = {}

        if parse_command_line_args:
            # parse command-line arguments to override TrainerArgs()
            coqpit_overrides = args.parse_known_args(arg_prefix="")

            # get ready for training and parse command-line arguments to override the model config
            config, new_fields = self.init_training(args, coqpit_overrides, config)
        elif args.continue_path or args.restore_path:
            config, new_fields = self.init_training(args, [], config)
        else:
            new_fields = {}

        # set the output path
        if args.continue_path:
            self.continue_run = True
            # use the same path as the continuing run
            output_path = args.continue_path
        else:
            self.continue_run = False
            # override the output path if it is provided
            output_path = config.output_path if output_path is None else str(output_path)
            # create a new output folder name
            output_path = get_experiment_folder_path(output_path, config.run_name)
            output_path.mkdir(exist_ok=True, parents=True)

        # copy training assets to the output folder
        copy_model_files(config, output_path, new_fields)

        # init class members
        self.args = args
        self.config = config
        self.output_path = Path(output_path)
        self.training_assets = training_assets
        self.grad_accum_steps = args.grad_accum_steps
        self.overfit_batch = args.overfit_batch
        self.skip_train_epoch = args.skip_train_epoch
        self.start_with_eval = args.start_with_eval

        assert self.grad_accum_steps > 0, " [!] grad_accum_steps must be greater than 0."

        # setup logging
        log_file = os.path.join(self.output_path, f"trainer_{args.rank}_log.txt")
        self._setup_logger_config(log_file)

        # setup training environment
        self.use_cuda, self.num_gpus = self.setup_training_environment(args=args, config=config, gpu=gpu)

        # init loggers
        self.dashboard_logger, self.c_logger = self.init_loggers(self.config, output_path, dashboard_logger, c_logger)
        # self.c_logger.logger = logger

        self.log_model_step = (
            self.config.log_model_step if self.config.log_model_step is not None else self.config.save_step
        )

        # make sure that start_with_eval is disabled if eval is disabled
        if not self.config.run_eval and self.start_with_eval:
            self.start_with_eval = False

        self.total_steps_done = 0
        self.epochs_done = 0
        self.best_loss: LossDict | float = {
            "train_loss": float("inf"),
            "eval_loss": float("inf") if self.config.run_eval else None,
        }
        self.train_loader: DataLoader[Any] | None = None
        self.test_loader: DataLoader[Any] | None = None
        self.eval_loader: DataLoader[Any] | None = None

        self.keep_avg_train: KeepAverage | None = None
        self.keep_avg_eval: KeepAverage | None = None

        self.use_amp_scaler = (
            self.use_cuda
            if self.config.mixed_precision and self.config.precision == "fp16"
            else self.config.use_grad_scaler
        )

        self.train_samples: list[Any] | None
        self.eval_samples: list[Any] | None
        self.test_samples: list[Any] | None
        if train_samples is not None:
            # use the provided samples
            self.train_samples = train_samples
            self.eval_samples = eval_samples
            self.test_samples = test_samples
        elif get_data_samples is not None:
            # run `get_data_samples` to init the data samples
            (
                self.train_samples,
                self.eval_samples,
                self.test_samples,
            ) = self.run_get_data_samples(config, get_data_samples)
        else:
            # expecting to load the samples in `model.get_data_loader()`
            self.train_samples = None
            self.eval_samples = None
            self.test_samples = None

        # define custom train and eval loader
        self.train_loader = train_loader
        self.eval_loader = eval_loader

        # only use a subset of the samples if small_run is set
        self.setup_small_run(args.small_run)

        # init the model
        if model is not None:
            self.model = model
        elif get_model is not None:
            self.run_get_model(self.config, get_model)
        else:
            msg = "`model` and `get_model` cannot both be None."
            raise ValueError(msg)

        # init model's training assets
        self.model.init_for_training()

        # setup criterion
        self.criterion = self.get_criterion(self.model)

        # DISTRUBUTED
        if self.use_pt_ddp:
            rank_zero_logger_info(" > Using PyTorch DDP", logger)
            init_distributed(
                args.rank,
                self.num_gpus,
                args.group_id,
                self.config.distributed_backend,
                self.config.distributed_url,
            )

        if self.use_cuda:
            self.model.cuda()
            if isinstance(self.criterion, list):
                for criterion in self.criterion:
                    if isinstance(criterion, nn.Module):
                        criterion.cuda()
            elif isinstance(self.criterion, nn.Module):
                self.criterion.cuda()

        # setup optimizer and scheduler
        self.optimizer = self.get_optimizer(self.model, self.config)
        self.scheduler = self.get_scheduler(self.model, self.config, self.optimizer)
        # With multiple optimizers, some are not used all the time. We keep
        # track of that to know whether to step the corresponding schedulers.
        self._stepped_optimizers: set[int | None] = set()

        # CALLBACK
        self.callbacks = TrainerCallback()
        self.callbacks.parse_callbacks_dict(callbacks)
        self.callbacks.on_init_start(self)

        # init AMP
        self.scaler = GradScaler() if self.use_amp_scaler else None

        # restore model
        if self.args.restore_path:
            self.restore_model()

        # DISTRIBUTED
        self.wrapped_model: TrainerModel | None = None
        if self.use_pt_ddp:
            ddp_model = DDP_th(self.model, device_ids=[args.rank], output_device=args.rank)
            self.wrapped_model = ddp_model.module  # cast(TrainerModel, ddp_model.module)

        # setup accelerator
        self.setup_accelerate()

        # count model size
        num_params = count_parameters(self.model)
        rank_zero_logger_info(f"\n > Model has {num_params} parameters", logger)

        self.callbacks.on_init_end(self)
        self.dashboard_logger.add_config(config)
        self.save_training_script()

    @property
    def use_pt_ddp(self) -> bool:
        """Return True if using PyTorch DDP."""
        return self.num_gpus > 1 and not self.use_accelerate

    @property
    def use_accelerate(self) -> bool:
        """Return True if using HF Accelerate."""
        return self.args.use_accelerate

    def setup_accelerate(self) -> None:
        if self.use_accelerate:
            self.model, self.optimizer, self.train_loader, self.scheduler, self.accelerator = self.init_accelerate(
                model=self.model,
                optimizer=self.optimizer,
                training_dataloader=self.train_loader,
                scheduler=self.scheduler,
                grad_accum_steps=self.grad_accum_steps,
                mixed_precision=self.config.mixed_precision,
                precision=self.config.precision,
            )

    def prepare_accelerate_loader(self, data_loader: DataLoader[Any]) -> DataLoader[Any]:
        """Prepare the accelerator for the training."""
        if self.use_accelerate:
            return self.accelerator.prepare_data_loader(data_loader)
        return data_loader

    @staticmethod
    def init_accelerate(
        model: TrainerModel,
        optimizer: ValueListDict[torch.optim.Optimizer],
        training_dataloader: DataLoader[Any] | None,
        scheduler: LRScheduler | list[LRScheduler] | dict[str, LRScheduler] | None,
        *,
        grad_accum_steps: int,
        mixed_precision: bool,
        precision: str,
    ) -> tuple:
        """Setup HF Accelerate for the training."""
        # check if accelerate is installed
        try:
            from accelerate import Accelerator  # pylint:disable=import-outside-toplevel
        except ImportError as e:
            msg = "Please install accelerate to use this feature."
            raise ImportError(msg) from e

        _precision = precision if precision is not None else "f16" if mixed_precision else None
        if _precision == "float16":
            _precision = "f16"
        elif _precision == "float8":
            _precision = "f8"
        elif _precision == "bfloat16":
            _precision = "bf16"
        accelerator = Accelerator(gradient_accumulation_steps=grad_accum_steps, mixed_precision=_precision)
        if isinstance(model, nn.Module):
            model = accelerator.prepare_model(model)

        optimizer = map_value_list_dict(optimizer, accelerator.prepare_optimizer)

        if isinstance(training_dataloader, torch.utils.data.DataLoader):
            training_dataloader = accelerator.prepare_data_loader(training_dataloader)

        if scheduler is not None:
            scheduler = map_value_list_dict(scheduler, accelerator.prepare_scheduler)

        return model, optimizer, training_dataloader, scheduler, accelerator

    def save_training_script(self) -> None:
        """Save the training script to tracking dashboard and output path."""
        file_path = Path(sys.argv[0])
        if file_path.is_file():
            file_name = file_path.name
            self.dashboard_logger.add_artifact(file_or_dir=file_path, name=file_name, artifact_type="file")
            with file_path.open(encoding="utf8") as f:
                self.dashboard_logger.add_text("training-script", f"{f.read()}", 0)
            shutil.copyfile(file_path, self.output_path / file_name)

    @staticmethod
    def init_loggers(
        config: TrainerConfig,
        output_path: str | os.PathLike[Any],
        dashboard_logger: BaseDashboardLogger | None = None,
        c_logger: ConsoleLogger | None = None,
    ) -> tuple[BaseDashboardLogger, ConsoleLogger]:
        """Init console and dashboard loggers.

        Use the given logger if passed externally else use config values to pick the right logger.
        Return a dashboard logger only for the rank 0 process in DDP
        Define a console logger for each process in DDP

        Args:
            config (TrainerConfig): Model config.
            output_path (str): Output path to save the training artifacts.
            dashboard_logger (DashboardLogger): Object passed to the trainer from outside.
            c_logger (ConsoleLogger): Object passed to the trained from outside.

        Returns:
            Initialized dashboard_logger and console_logger objects.
        """
        c_logger = ConsoleLogger() if c_logger is None else c_logger

        # only allow dashboard logging for the main process in DDP mode
        if get_rank() > 0:
            return DummyLogger(), c_logger
        if dashboard_logger is None:
            dashboard_logger = logger_factory(config, output_path)
        return dashboard_logger, c_logger

    def setup_small_run(self, small_run: int | None = None) -> None:
        """Use a subset of samples for training, evaluation and testing."""
        if small_run is not None:
            logger.info("[!] Small Run, only using %i samples.", small_run)
            self.train_samples = None if self.train_samples is None else self.train_samples[:small_run]
            self.eval_samples = None if self.eval_samples is None else self.eval_samples[:small_run]
            self.test_samples = None if self.test_samples is None else self.test_samples[:small_run]

    @staticmethod
    def init_training(
        args: TrainerArgs, coqpit_overrides: list[str], config: TrainerConfig | None = None
    ) -> tuple[TrainerConfig, dict[str, str]]:
        """Initialize training and update model configs from command line arguments.

        Args:
            args: Parsed trainer arguments.
            config_overrides: Parsed config overriding arguments.
            config: Model config. If none, it is generated from `args`. Defaults to None.

        Returns:
            config (TrainerConfig): Config paramaters.
        """
        # set arguments for continuing training
        if args.continue_path:
            config_path = os.path.join(args.continue_path, "config.json")
            args.restore_path, best_model = get_last_checkpoint(args.continue_path)
            if not args.best_path:
                args.best_path = best_model
            # use the same config
            if config:
                config.load_json(config_path)
            else:
                config = TrainerConfig()
                config.load_json(config_path)

        if config is None:
            msg = "Config or continue_path containing Config not provided"
            raise ValueError(msg)

        # override config values from command-line args
        # TODO: Maybe it is better to do it outside
        if len(coqpit_overrides) > 0:
            config.parse_known_args(coqpit_overrides, relaxed_parser=True)

        # update the config.json fields and copy it to the output folder
        new_fields = {}
        if args.rank == 0:
            if args.restore_path:
                new_fields["restore_path"] = args.restore_path
            new_fields["github_branch"] = get_git_branch()
        return config, new_fields

    @staticmethod
    def setup_training_environment(args: TrainerArgs, config: TrainerConfig, gpu: int | None) -> tuple[bool, int]:
        if platform.system() != "Windows":
            # https://github.com/pytorch/pytorch/issues/973
            import resource  # pylint: disable=import-outside-toplevel

            rlimit = resource.getrlimit(resource.RLIMIT_NOFILE)
            resource.setrlimit(resource.RLIMIT_NOFILE, (4096, rlimit[1]))

        # set and initialize Pytorch runtime
        use_cuda, num_gpus = setup_torch_training_env(
            args=args,
            cudnn_enable=config.cudnn_enable,
            cudnn_deterministic=config.cudnn_deterministic,
            cudnn_benchmark=config.cudnn_benchmark,
            use_ddp=args.use_ddp,
            training_seed=config.training_seed,
            allow_tf32=config.allow_tf32,
            gpu=gpu if args.gpu is None else args.gpu,
        )

        print_training_env(args, config)
        return use_cuda, num_gpus

    @staticmethod
    @overload
    def run_get_model(config: TrainerConfig, get_model: Callable[[TrainerConfig], TrainerModel]) -> TrainerModel: ...

    @staticmethod
    @overload
    def run_get_model(config: TrainerConfig, get_model: Callable[[], TrainerModel]) -> TrainerModel: ...

    @staticmethod
    def run_get_model(config: TrainerConfig, get_model: Callable[..., TrainerModel]) -> TrainerModel:
        """Run the `get_model` function and return the model.

        Args:
            config (TrainerConfig): Model config.

        Returns:
            TrainerModel: initialized model.
        """
        return get_model(config) if len(signature(get_model).parameters) == 1 else get_model()

    @staticmethod
    def run_get_data_samples(
        config: TrainerConfig, get_data_samples: Callable[..., list[Any]]
    ) -> tuple[list[Any] | None, list[Any] | None, list[Any] | None]:
        if callable(get_data_samples):
            if len(signature(get_data_samples).parameters) == 1:
                train_samples, eval_samples, test_samples = get_data_samples(config)
            else:
                train_samples, eval_samples, test_samples = get_data_samples()
            return train_samples, eval_samples, test_samples
        return None, None, None

    def restore_model(self) -> None:
        """Restore training from an old run.

        It restores model, optimizer, AMP scaler and training stats.
        """

        def _restore_list_objs(states: Any, obj: Any) -> None:
            if isinstance(obj, list):
                for idx, state in enumerate(states):
                    obj[idx].load_state_dict(state)
            elif isinstance(obj, dict):
                for key, state in states.items():
                    obj[key].load_state_dict(state)
            else:
                obj.load_state_dict(states)

        verb = "Continuing" if self.continue_run else "Restoring"
        logger.info(" > %s from %s ...", verb, os.path.basename(self.args.restore_path))
        checkpoint = load_fsspec(self.args.restore_path, map_location="cpu")

        try:
            logger.info(" > Restoring Model...")
            self.model.load_state_dict(checkpoint["model"])
            if self.continue_run:
                logger.info(" > Restoring Optimizer...")
                try:
                    _restore_list_objs(checkpoint["optimizer"], self.optimizer)
                except (KeyError, TypeError, RuntimeError):
                    logger.info(" > Optimizer is not compatible with the restored model.")
                if checkpoint.get("scheduler"):
                    logger.info(" > Restoring Scheduler...")
                    _restore_list_objs(checkpoint["scheduler"], self.scheduler)
                if "scaler" in checkpoint and self.use_amp_scaler and checkpoint["scaler"]:
                    logger.info(" > Restoring Scaler...")
                    _restore_list_objs(checkpoint["scaler"], self.scaler)
        except (KeyError, RuntimeError, ValueError):
            logger.info(" > Partial model initialization...")
            model_dict = self.model.state_dict()
            model_dict = set_partial_state_dict(model_dict, checkpoint["model"], self.config)
            self.model.load_state_dict(model_dict)
            del model_dict

        self.total_steps_done = checkpoint["step"] + 1  # +1 not to immediately checkpoint if the model is restored
        self.epochs_done = checkpoint["epoch"]

        if not self.continue_run:
            self.total_steps_done = 0
            self.epochs_done = 0
            # Use LR read from the checkpoint if we continue a training run
            self.reset_lr()

        logger.info(" > Model restored from step %i", checkpoint["step"])
        torch.cuda.empty_cache()

    def reset_lr(self) -> None:
        """Reset learning rate to default values."""
        for key, optim in iter_value_list_dict(self.optimizer):
            for group in optim.param_groups:
                lr = self.get_lr(self.model, self.config)
                group["lr"] = lr[key] if key is not None else lr  # type: ignore[index]

    #########################
    # DATA LOADING FUNCTIONS
    #########################

    def _get_loader(
        self,
        model: TrainerModel,
        config: TrainerConfig,
        assets: dict[str, Any],
        samples: list[Any] | None,
        *,
        is_eval: bool,
        verbose: bool,
        num_gpus: int,
    ) -> DataLoader[Any]:
        loader = model.get_data_loader(
            config=config,
            assets=assets,
            is_eval=is_eval,
            samples=samples,
            verbose=verbose,
            num_gpus=num_gpus,
            rank=self.args.rank,
        )

        assert len(loader) > 0, (
            " ❗ len(DataLoader) returns 0. Make sure your dataset is not empty or len(dataset) > 0. "
        )
        return loader

    def _get_model(self) -> TrainerModel:
        if not hasattr(self, "wrapped_model") or self.wrapped_model is None:
            return self.model
        return self.wrapped_model

    def get_train_dataloader(
        self, training_assets: dict[str, Any], samples: list[Any] | None, *, verbose: bool = True
    ) -> DataLoader[Any]:
        """Initialize and return a training data loader.

        Call ```model.get_train_data_loader``` if it is implemented, else call ```model.get_data_loader```
        and set ```is_eval=False```.

        Args:
            ap (AudioProcessor): Audio processor.
            samples (List): Data samples used for training.
            verbose (bool): enable/disable printing loader stats at initialization.

        Returns:
            DataLoader: Initialized training data loader.
        """
        model = self._get_model()
        try:
            return model.get_train_data_loader(
                self.config,
                self.training_assets,
                samples,
                verbose,
                self.num_gpus,
                self.args.rank,
            )
        except NotImplementedError:
            return self._get_loader(
                model,
                self.config,
                training_assets,
                samples,
                is_eval=False,
                verbose=verbose,
                num_gpus=self.num_gpus,
            )

    def get_eval_dataloader(
        self, training_assets: dict[str, Any], samples: list[Any] | None, *, verbose: bool
    ) -> DataLoader[Any]:
        """Initialize and return a evaluation data loader.

        Call ```model.get_eval_data_loader``` if it is implemented, else call ```model.get_data_loader```
        and set ```is_eval=True```.

        Args:
            ap (AudioProcessor): Audio processor.
            samples (List): Data samples used for training.
            verbose (bool): enable/disable printing loader stats at initialization.

        Returns:
            DataLoader: Initialized training data loader.
        """
        model = self._get_model()
        try:
            return model.get_eval_data_loader(
                self.config,
                self.training_assets,
                samples,
                verbose,
                self.num_gpus,
                self.args.rank,
            )
        except NotImplementedError:
            return self._get_loader(
                model,
                self.config,
                training_assets,
                samples,
                is_eval=True,
                verbose=verbose,
                num_gpus=self.num_gpus,
            )

    def get_test_dataloader(
        self, training_assets: dict[str, Any], samples: list[Any] | None, *, verbose: bool
    ) -> DataLoader[Any]:
        """Initialize and return a evaluation data loader.

        Call ```model.get_test_data_loader``` if it is implemented, else call ```model.get_data_loader```
        and set ```is_eval=True```.

        Args:
            ap (AudioProcessor): Audio processor.
            samples (List): Data samples used for training.
            verbose (bool): enable/disable printing loader stats at initialization.

        Returns:
            DataLoader: Initialized training data loader.
        """
        model = self._get_model()
        try:
            return model.get_test_data_loader(
                self.config,
                self.training_assets,
                samples,
                verbose,
                self.num_gpus,
                self.args.rank,
            )
        except NotImplementedError:
            return self._get_loader(
                model,
                self.config,
                training_assets,
                samples,
                is_eval=True,
                verbose=verbose,
                num_gpus=self.num_gpus,
            )

    def format_batch(self, batch: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
        """Format the dataloader output and return a batch.

        1. Call ```model.format_batch```.
        2. Pass the batch to the Device.
        3. Call ```model.format_batch_on_device```.

        Args:
            batch (List): Batch returned by the dataloader.

        Returns:
            Dict: Formatted batch.
        """
        with suppress(NotImplementedError):
            batch = (
                self.wrapped_model.format_batch(batch)
                if self.wrapped_model is not None
                else self.model.format_batch(batch)
            )

        if isinstance(batch, dict):
            for k, v in batch.items():
                batch[k] = to_cuda(v)
        elif isinstance(batch, list):
            batch = [to_cuda(v) for v in batch]

        with suppress(NotImplementedError):
            batch = (
                self.wrapped_model.format_batch_on_device(batch)
                if self.wrapped_model is not None
                else self.model.format_batch_on_device(batch)
            )
        return batch

    ######################
    # TRAIN FUNCTIONS
    ######################

    @staticmethod
    def master_params(optimizer: torch.optim.Optimizer) -> Generator[Any]:
        """Generator over parameters owned by the optimizer.

        Used to select parameters used by the optimizer for gradient clipping.

        Args:
            optimizer: Target optimizer.
        """
        for group in optimizer.param_groups:
            yield from group["params"]

    def _model_train_step(
        self,
        batch: dict[str, Any] | list[Any],
        criterion: nn.Module | list[nn.Module],
        optimizer_idx: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Perform a training forward step. Compute model outputs and losses.

        Args:
            batch (Dict): [description]
            criterion (nn.Module): [description]
            optimizer_idx (int, optional): [description]. Defaults to None.

        Returns:
            Tuple[Dict, Dict]: Model outputs and losses
        """
        input_args: list[Any] = [batch, criterion]
        if optimizer_idx is not None:
            input_args.append(optimizer_idx)
        # unwrap model in DDP training
        if self.wrapped_model is not None:
            return self.wrapped_model.train_step(*input_args)
        return self.model.train_step(*input_args)

    def _get_autocast_args(self, *, mixed_precision: bool, precision: str) -> tuple[str, torch.dtype]:
        device = "cpu"
        dtype = torch.get_autocast_dtype("cpu") if is_pytorch_at_least_2_4() else torch.get_autocast_cpu_dtype()
        if self.use_cuda:
            device = "cuda"
            dtype = torch.float32
            if mixed_precision:
                if precision == "fp16":
                    dtype = torch.float16
                elif precision == "bf16":
                    dtype = torch.bfloat16
                else:
                    msg = f" ❗ Unknown precision {precision}"
                    raise ValueError(msg)
        elif mixed_precision:
            dtype = torch.bfloat16
        return device, dtype

    def detach_loss_dict(
        self,
        loss_dict: dict[str, Any],
        *,
        step_optimizer: bool,
        optimizer_idx: int | None = None,
        grad_norm: torch.Tensor | float | None = None,
    ) -> dict[str, Any]:
        # detach losses for logging
        loss_dict_detached = self._detach_loss_dict(loss_dict)
        # loss_dict_detached["loss"] = loss_di`ct_detached["loss"] * float(self.grad_accum_steps)

        if optimizer_idx is not None:
            loss_dict_detached[f"loss_{optimizer_idx}"] = loss_dict_detached.pop("loss")
            if step_optimizer and grad_norm is not None:
                loss_dict_detached[f"grad_norm_{optimizer_idx}"] = grad_norm
        elif step_optimizer and grad_norm is not None:
            loss_dict_detached["grad_norm"] = grad_norm
        return loss_dict_detached

    def _compute_loss(
        self,
        batch: dict[str, Any] | list[Any],
        criterion: nn.Module | list[nn.Module],
        optimizer_idx: int | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        device, dtype = self._get_autocast_args(
            mixed_precision=self.config.mixed_precision, precision=self.config.precision
        )
        with torch.autocast(device_type=device, dtype=dtype, enabled=self.config.mixed_precision):
            if optimizer_idx is not None:
                outputs, loss_dict = self._model_train_step(batch, criterion, optimizer_idx=optimizer_idx)
            else:
                outputs, loss_dict = self._model_train_step(batch, criterion)
        return outputs, loss_dict

    @staticmethod
    def _set_grad_clip_per_optimizer(config: TrainerConfig, optimizer_idx: int | None) -> float:
        # set gradient clipping threshold
        grad_clip: float = 0.0  # meaning no gradient clipping
        if "grad_clip" in config and config.grad_clip is not None:
            if optimizer_idx is not None:
                if isinstance(config.grad_clip, list):
                    grad_clip = config.grad_clip[optimizer_idx]
                else:
                    logger.warning(" [!] You are using multiple optimizers but `grad_clip` is not a list.")
            else:
                if isinstance(config.grad_clip, list):
                    msg = "`grad_clip` is a list, but no optimizer_idx specified"
                    raise ValueError(msg)
                grad_clip = config.grad_clip
        return grad_clip

    def _compute_grad_norm(self, optimizer: torch.optim.Optimizer) -> torch.Tensor:
        return torch.norm(torch.cat([param.grad.view(-1) for param in self.master_params(optimizer)], dim=0), p=2)

    def _grad_clipping(
        self, grad_clip: float, optimizer: torch.optim.Optimizer, scaler: Optional["torch.GradScaler"]
    ) -> torch.Tensor:
        """Perform gradient clipping."""
        if grad_clip is not None and grad_clip > 0:
            if scaler:
                scaler.unscale_(optimizer)
            self.callbacks.before_gradient_clipping(self)
            grad_norm = torch.nn.utils.clip_grad_norm_(self.master_params(optimizer), grad_clip)
        else:
            grad_norm = self._compute_grad_norm(optimizer)
        return grad_norm

    def optimize(
        self,
        batch: dict[str, Any] | list[Any],
        optimizer: torch.optim.Optimizer,
        scaler: "torch.GradScaler | None",
        criterion: nn.Module | list[nn.Module],
        scheduler: LRScheduler | None,
        *,
        optimizer_idx: int | None = None,
        step_optimizer: bool = True,
        num_optimizers: int = 1,
    ) -> tuple[dict[str, Any], dict[str, Any], float]:
        """Perform a forward - backward pass and run the optimizer.

        Args:
            batch (Dict): Input batch. If
            optimizer (Union[nn.optim.Optimizer, List]): Model's optimizer. If it is a list then, `optimizer_idx` must be defined to indicate the optimizer in use.
            scaler (AMPScaler): AMP scaler.
            criterion (nn.Module): Model's criterion.
            scheduler (LRScheduler): LR scheduler used by the optimizer.
            optimizer_idx (int, optional): Target optimizer being used. Defaults to None.
            step_optimizer (bool, optional): Whether step the optimizer. If False, gradients are accumulated and
                model parameters are not updated. Defaults to True.
            num_optimizers (int, optional): Number of optimizers. Defaults to 1.

        Raises:
            RuntimeError: When the loss is NaN.

        Returns:
            Tuple[Dict, Dict, int, torch.Tensor]: model outputs, losses, step time and gradient norm.
        """
        step_start_time = time.time()

        # forward pass and loss computation
        outputs, loss_dict = self._compute_loss(batch=batch, criterion=criterion, optimizer_idx=optimizer_idx)

        # skip the rest if not outputs from the model
        if not loss_dict:
            step_time = time.time() - step_start_time
            return outputs, {}, step_time

        grad_clip = self._set_grad_clip_per_optimizer(config=self.config, optimizer_idx=optimizer_idx)
        # optimizer step
        grad_norm: float | torch.Tensor = 0.0
        update_lr_scheduler = True

        # callback
        self.callbacks.before_backward_pass(self, loss_dict)

        # accumulated gradients adjustment
        loss_dict["loss"] = loss_dict["loss"] / float(self.grad_accum_steps)

        if self.use_accelerate:
            with self.accelerator.accumulate(self.model):
                ctx_mgr = self.accelerator.autocast if self.config.mixed_precision else nullcontext
                with ctx_mgr():
                    self.accelerator.backward(loss_dict["loss"])
                    grad_norm = self._compute_grad_norm(optimizer)
                    if self.accelerator.sync_gradients and grad_clip is not None and grad_clip > 0:
                        self.accelerator.clip_grad_norm_(self.model.parameters(), grad_clip)
                    optimizer.step()
                    self._stepped_optimizers.add(optimizer_idx)
                    if (
                        scheduler is not None
                        and not self.config.scheduler_after_epoch
                        and not self.accelerator.optimizer_step_was_skipped
                    ):
                        scheduler.step()
                    optimizer.zero_grad(set_to_none=True)
        else:
            if self.use_amp_scaler and scaler is not None:
                # model optimizer step in mixed precision mode
                scaler.scale(loss_dict["loss"]).backward()
                # gradient accumulation
                if step_optimizer:
                    grad_norm = self._grad_clipping(grad_clip=grad_clip, optimizer=optimizer, scaler=scaler)
                    scale_prev = scaler.get_scale()
                    scaler.step(optimizer)
                    # update the scaler at the end of all the optimizer steps
                    if optimizer_idx is None or (optimizer_idx + 1 == num_optimizers):
                        scaler.update()
                        loss_dict["amp_scaler"] = scaler.get_scale()  # for logging
                    update_lr_scheduler = scale_prev <= scaler.get_scale()
            else:
                # main model optimizer step
                loss_dict["loss"].backward()
                # gradient accumulation
                if step_optimizer:
                    self.callbacks.before_gradient_clipping(self)
                    if grad_clip > 0:
                        grad_norm = torch.nn.utils.clip_grad_norm_(self.master_params(optimizer), grad_clip)
                    optimizer.step()
                    self._stepped_optimizers.add(optimizer_idx)

            # setup lr
            if (
                scheduler is not None
                and update_lr_scheduler
                and not self.config.scheduler_after_epoch
                and step_optimizer
            ):
                scheduler.step()

            # zero-out optimizer
            if step_optimizer:
                optimizer.zero_grad(set_to_none=True)

        # pytorch skips the step when the norm is 0. So ignore the norm value when it is NaN
        if isinstance(grad_norm, torch.Tensor) and (torch.isnan(grad_norm) or torch.isinf(grad_norm)):
            grad_norm = 0

        step_time = time.time() - step_start_time

        # detach loss dict
        loss_dict_detached = self.detach_loss_dict(
            loss_dict, step_optimizer=step_optimizer, optimizer_idx=optimizer_idx, grad_norm=grad_norm
        )
        return outputs, loss_dict_detached, step_time

    def train_step(
        self, batch: dict[str, Any] | list[Any], batch_n_steps: int, step: int, loader_start_time: float
    ) -> tuple[dict[str, Any] | list[dict[str, Any]] | None, dict[str, Any] | None]:
        """Perform a training step on a batch of inputs and log the process.

        Args:
            batch (Dict): Input batch.
            batch_n_steps (int): Number of steps needed to complete an epoch. Needed for logging.
            step (int): Current step number in this epoch.
            loader_start_time (float): The time when the data loading is started. Needed for logging.

        Returns:
            Tuple[Dict, Dict]: Model outputs and losses.
        """
        self.callbacks.on_train_step_start(self)
        # format data
        batch = self.format_batch(batch)
        loader_time = time.time() - loader_start_time

        # containers to hold model outputs and losses for each optimizer.
        outputs: dict[str, Any] | list[dict[str, Any]]
        loss_dict = {}

        # log learning rates (do it before they're updated in optimize())
        lrs = {}
        for key, optim in iter_value_list_dict(self.optimizer):
            name = f"current_lr_{key}" if key is not None else "current_lr"
            lrs[name] = optim.param_groups[0]["lr"]
        loss_dict.update(lrs)

        # OPTIMIZATION
        try:
            # custom optimize for the model
            step_time = time.time()
            device, dtype = self._get_autocast_args(
                mixed_precision=self.config.mixed_precision, precision=self.config.precision
            )
            with torch.autocast(device_type=device, dtype=dtype, enabled=self.config.mixed_precision):
                outputs, loss_dict_new = self.model.optimize(batch, self)
            step_time = time.time() - step_time
            # If None, skip the step
            if outputs is None:
                return None, None
            # TODO: find a way to log grad_norm for custom optimize
            loss_dict_new = self.detach_loss_dict(loss_dict_new, step_optimizer=True)
            loss_dict.update(loss_dict_new)
        except NotImplementedError as e:
            # gradient accumulation
            # TODO: grad accumulation for each optimizer
            step_optimizer = True
            if ((step + 1) % self.grad_accum_steps != 0) and (step + 1 != batch_n_steps):
                step_optimizer = False

            if not isinstance(self.optimizer, list):
                if isinstance(self.scheduler, list):
                    msg = "Can't use list of schedulers with a single optimizer."
                    raise TypeError(msg) from e
                if isinstance(self.optimizer, dict) or isinstance(self.scheduler, dict):
                    msg = "Can only use dict of optimizers/schedulers with custom `optimize()`"
                    raise TypeError(msg) from e
                # auto training with a single optimizer
                outputs, loss_dict_new, step_time = self.optimize(
                    batch,
                    self.optimizer,
                    self.scaler,
                    self.criterion,
                    self.scheduler,
                    step_optimizer=step_optimizer,
                    num_optimizers=1,
                )
                loss_dict.update(loss_dict_new)
            else:
                if self.grad_accum_steps != 1:
                    msg = " [!] Coqui Trainer does not support grad_accum_steps for multiple-optimizer setup, please set grad_accum_steps to 1 or implement in your model a custom `optimize` method to deal with dangling gradients in multiple-optimizer setup!"
                    raise ValueError(msg) from e
                # auto training with multiple optimizers (e.g. GAN)
                outputs_per_optimizer = []
                total_step_time = 0.0
                for idx, optimizer in enumerate(self.optimizer):
                    criterion = self.criterion
                    # scaler = self.scaler[idx] if self.use_amp_scaler else None
                    scaler = self.scaler
                    scheduler = None
                    if self.scheduler is not None and isinstance(self.scheduler, list):
                        scheduler = self.scheduler[idx]
                    optimizer_outputs, loss_dict_new, step_time = self.optimize(
                        batch,
                        optimizer,
                        scaler,
                        criterion,
                        scheduler,
                        optimizer_idx=idx,
                        step_optimizer=step_optimizer,
                        num_optimizers=len(self.optimizer),
                    )
                    # skip the rest if the model returns None
                    total_step_time += step_time
                    outputs_per_optimizer.append(optimizer_outputs)
                    # merge loss_dicts from each optimizer
                    # rename duplicates with the optimizer idx
                    # if None, model skipped this optimizer
                    if loss_dict_new is not None:
                        for k, v in loss_dict_new.items():
                            if k in loss_dict:
                                loss_dict[f"{k}-{idx}"] = v
                            else:
                                loss_dict[k] = v
                    step_time = total_step_time

                outputs = outputs_per_optimizer

                # clear any pesky gradients after gradient accumulation
                if step_optimizer:
                    self.model.zero_grad(set_to_none=True)

        if self.keep_avg_train is not None:
            # update avg runtime stats
            keep_avg_update = {}
            keep_avg_update["avg_loader_time"] = loader_time
            keep_avg_update["avg_step_time"] = step_time
            self.keep_avg_train.update_values(keep_avg_update)

            # update avg loss stats
            update_eval_values = {}
            for key, value in loss_dict.items():
                update_eval_values["avg_" + key] = value
            self.keep_avg_train.update_values(update_eval_values)

        # print training progress
        if self.total_steps_done % self.config.print_step == 0:
            # log run-time stats
            loss_dict.update(
                {
                    "step_time": round(step_time, 4),
                    "loader_time": round(loader_time, 4),
                }
            )
            self.c_logger.print_train_step(
                batch_n_steps,
                step,
                self.total_steps_done,
                loss_dict,
                self.keep_avg_train.avg_values if self.keep_avg_train is not None else {},
            )

        if self.args.rank == 0:
            # Plot Training Iter Stats
            # reduce TB load and don't log every step
            if self.total_steps_done % self.config.plot_step == 0:
                self.dashboard_logger.train_step_stats(self.total_steps_done, loss_dict)
            if (
                self.total_steps_done % self.config.save_step == 0
                and self.total_steps_done != 0
                and self.config.save_checkpoints
            ):
                self.save_checkpoint()

            if self.total_steps_done % self.log_model_step == 0:
                # log checkpoint as artifact
                self.update_training_dashboard_logger(batch=batch, outputs=outputs)

            self.dashboard_logger.flush()

        self.total_steps_done += 1
        self.callbacks.on_train_step_end(self)
        return outputs, loss_dict

    def train_epoch(self) -> None:
        """Main entry point for the training loop. Run training on the all training samples."""
        # initialize the data loader
        if self.train_loader is None:
            self.train_loader = self.get_train_dataloader(
                self.training_assets,
                self.train_samples,
                verbose=True,
            )
            self.train_loader = self.prepare_accelerate_loader(self.train_loader)
        # set model to training mode
        self.model.train()
        epoch_start_time = time.time()

        self.callbacks.on_train_epoch_start(self)

        self.c_logger.print_train_start()
        loader_start_time = time.time()
        # TRAINING EPOCH -> iterate over the training samples
        batch_num_steps = len(self.train_loader)
        for cur_step, batch in enumerate(self.train_loader):
            outputs, _ = self.train_step(batch, batch_num_steps, cur_step, loader_start_time)
            if outputs is None:
                logger.info(" [!] `train_step()` retuned `None` outputs. Skipping training step.")
                continue
            del outputs
            loader_start_time = time.time()

            # RUN EVAL -> run evaluation epoch in the middle of training. Useful for big datasets.
            if self.config.run_eval_steps is not None and (self.total_steps_done % self.config.run_eval_steps == 0):
                self.eval_epoch()
                self.model.train()

        epoch_time = time.time() - epoch_start_time
        self.callbacks.on_train_epoch_end(self)

        # scheduler step
        if self.scheduler is not None and self.config.scheduler_after_epoch:
            for idx, scheduler in iter_value_list_dict(self.scheduler):
                if scheduler is not None and idx in self._stepped_optimizers:
                    scheduler.step()
        self._stepped_optimizers.clear()
        # plot self.epochs_done Stats
        if self.args.rank == 0:
            epoch_stats = {"epoch_time": epoch_time}
            if self.keep_avg_train is not None:
                epoch_stats.update(self.keep_avg_train.avg_values)
            self.dashboard_logger.train_epoch_stats(self.total_steps_done, epoch_stats)
            if self.config.model_param_stats:
                self.dashboard_logger.model_weights(self.model, self.total_steps_done)
        torch.cuda.empty_cache()

    #######################
    # EVAL FUNCTIONS
    #######################

    def _model_eval_step(
        self,
        batch: dict[str, Any],
        model: TrainerModel,
        criterion: nn.Module | list[nn.Module],
        optimizer_idx: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Perform a evaluation forward pass. Compute model outputs and losses with no gradients.

        Args:
            batch (Dict): IBatch of inputs.
            model (TrainerModel): Model to call evaluation.
            criterion (nn.Module): Model criterion.
            optimizer_idx (int, optional): Optimizer ID to define the closure in multi-optimizer training. Defaults to None.

        Returns:
            Tuple[Dict, Dict]: model outputs and losses.
        """
        input_args: list[Any] = [batch, criterion]
        if optimizer_idx is not None:
            input_args.append(optimizer_idx)

        return self._get_model().eval_step(*input_args)

    def eval_step(
        self, batch: dict[str, Any] | list[Any], step: int
    ) -> tuple[dict[str, Any] | list[dict[str, Any]] | None, dict[str, Any] | None]:
        """Perform a evaluation step on a batch of inputs and log the process.

        Args:
            batch (Dict): Input batch.
            step (int): Current step number in this epoch.

        Returns:
            Tuple[Dict, Dict]: Model outputs and losses.
        """
        outputs: dict[str, Any] | list[dict[str, Any]]
        with torch.inference_mode():
            loss_dict: dict[str, Any] = {}
            model = self._get_model()
            if not isinstance(self.optimizer, list) or len(signature(model.eval_step).parameters) == 2:  # noqa: PLR2004
                outputs, loss_dict = model.eval_step(batch, self.criterion)
                if outputs is None:
                    return None, None
            else:
                optimizer_outputs = []
                for idx, _ in enumerate(self.optimizer):
                    outputs_, loss_dict_new = model.eval_step(batch, self.criterion, idx)
                    if outputs_ is None:
                        return None, None
                    optimizer_outputs.append(outputs_)

                    if loss_dict_new:
                        loss_dict_new[f"loss_{idx}"] = loss_dict_new.pop("loss")
                        loss_dict.update(loss_dict_new)
                outputs = optimizer_outputs

            loss_dict = self._detach_loss_dict(loss_dict)

            # update avg stats
            if self.keep_avg_eval is not None:
                update_eval_values = {}
                for key, value in loss_dict.items():
                    update_eval_values["avg_" + key] = value
                self.keep_avg_eval.update_values(update_eval_values)

            if self.config.print_eval:
                self.c_logger.print_eval_step(
                    step, loss_dict, self.keep_avg_eval.avg_values if self.keep_avg_eval is not None else {}
                )

        return outputs, loss_dict

    @torch.inference_mode()
    def eval_epoch(self) -> None:
        """Main entry point for the evaluation loop. Run evaluation on the all validation samples."""
        # initialize it when eval_epoch is called alone.
        self.keep_avg_eval = KeepAverage() if self.keep_avg_eval is None else self.keep_avg_eval

        if self.eval_loader is None:
            self.eval_loader = (
                self.get_eval_dataloader(
                    self.training_assets,
                    self.eval_samples,
                    verbose=True,
                )
                if self.config.run_eval
                else None
            )

        self.model.eval()
        self.c_logger.print_eval_start()
        loader_start_time = time.time()
        batch = None
        outputs = None
        for cur_step, batch in enumerate(self.eval_loader):  # type: ignore[arg-type]
            # format data
            batch = self.format_batch(batch)
            loader_time = time.time() - loader_start_time
            self.keep_avg_eval.update_values({"avg_loader_time": loader_time})
            outputs_, _ = self.eval_step(batch, cur_step)
            if outputs_ is None:
                logger.info(" [!] `eval_step()` retuned `None` outputs. Skipping evaluation step.")
                continue
            outputs = outputs_
            loader_start_time = time.time()
        # plot epoch stats, artifacts and figures
        if self.args.rank == 0 and outputs is not None:
            model = self._get_model()
            with suppress(NotImplementedError):
                model.eval_log(
                    batch,
                    outputs,
                    self.dashboard_logger,
                    self.training_assets,
                    self.total_steps_done,
                )
            self.dashboard_logger.eval_stats(self.total_steps_done, self.keep_avg_eval.avg_values)
        torch.cuda.empty_cache()

    ##################################
    # TESTING
    ##################################
    def test_run(self) -> None:
        """Run model test.

        Test run is expected to pass over test samples and produce logging artifacts.

        If ```model.test_run()``` is defined, it will be called and it is expected to set and execute everything
        in the model.

        Else if  ```mode.test()``` is defined, it will be called and it takes an test data loader as an argument
        and iterate over it.
        """
        self.model.eval()
        model = self._get_model()
        test_outputs = None
        try:
            test_outputs = model.test_run(self.training_assets)
        except NotImplementedError:
            self.test_loader = self.get_test_dataloader(
                self.training_assets,
                self.test_samples if self.test_samples else self.eval_samples,
                verbose=True,
            )
            # use test_loader to load test samples
            with suppress(NotImplementedError):
                test_outputs = model.test(self.training_assets, self.test_loader, None)
        with suppress(NotImplementedError):
            model.test_log(test_outputs, self.dashboard_logger, self.training_assets, self.total_steps_done)

    def _restore_best_loss(self) -> None:
        """Restore the best loss.

        Restore from the args.best_path if provided else from the model
        (`args.continue_path`) used for resuming the training.
        """
        if self.continue_run and (self.total_steps_done != 0 or self.args.best_path):
            logger.info(" > Restoring best loss from %s ...", os.path.basename(self.args.best_path))
            ch = load_fsspec(self.args.restore_path, map_location="cpu")
            if "model_loss" in ch:
                if isinstance(ch["model_loss"], dict):
                    self.best_loss = cast(LossDict, ch["model_loss"])
                # For backwards-compatibility:
                elif isinstance(ch["model_loss"], float):
                    if self.config.run_eval:
                        self.best_loss = {"train_loss": float("inf"), "eval_loss": ch["model_loss"]}
                    else:
                        self.best_loss = {"train_loss": ch["model_loss"], "eval_loss": None}
            logger.info(" > Starting with loaded last best loss %s", self.best_loss)

    def test(self, model: TrainerModel | None = None, test_samples: list[str] | None = None) -> None:
        """Run evaluation steps on the test data split.

        You can either provide the model and the test samples
        explicitly or the trainer uses values from the initialization.

        Args:
            model (TrainerModel, optional): Model to use for testing. If None, use the model given in the initialization.
                Defaults to None.

            test_samples (List[str], optional): List of test samples to use for testing. If None, use the test samples
                given in the initialization. Defaults to None.
        """
        logger.info(" > USING TEST SET...")
        self.keep_avg_eval = KeepAverage()

        if model is not None:
            self.model = model

        eval_samples_cache = self.eval_samples
        if test_samples is not None:
            self.eval_samples = test_samples
        else:
            self.eval_samples = self.test_samples

        self.eval_epoch()
        self.c_logger.print_epoch_end(self.epochs_done, self.keep_avg_eval.avg_values)
        self.eval_samples = eval_samples_cache

    ###################################
    # FIT FUNCTIONS
    ###################################

    def _fit(self) -> None:
        """🏃 train -> evaluate -> test for the number of epochs."""
        self._restore_best_loss()

        for epoch in range(self.epochs_done, self.config.epochs):
            if self.num_gpus > 1:
                # let all processes sync up before starting with a new epoch of training
                dist.barrier()
            self.callbacks.on_epoch_start(self)
            self.keep_avg_train = KeepAverage()
            self.keep_avg_eval = KeepAverage() if self.config.run_eval else None
            self.epochs_done = epoch
            self.c_logger.print_epoch_start(epoch, self.config.epochs, self.output_path)
            if not self.skip_train_epoch and not self.start_with_eval:
                self.train_epoch()
            if self.config.run_eval:
                self.eval_epoch()
            if epoch >= self.config.test_delay_epochs and self.args.rank <= 0:
                self.test_run()

            self.c_logger.print_epoch_end(
                epoch,
                self.keep_avg_eval.avg_values if self.config.run_eval else self.keep_avg_train.avg_values,  # type: ignore[union-attr]
            )
            if self.args.rank in [None, 0]:
                self.save_best_model()
            self.callbacks.on_epoch_end(self)
            self.start_with_eval = False

    def fit_with_largest_batch_size(self, starting_batch_size: int = 2048) -> None:
        cuda_meminfo()
        bs = starting_batch_size
        while True:
            gc.collect()
            torch.cuda.empty_cache()
            try:
                gc.collect()
                torch.cuda.empty_cache()
                self.config.batch_size = bs
                logger.info(" > current batch size: %i", self.config.batch_size)
                self._fit()
            except RuntimeError as exception:
                if bs > 1 and should_reduce_batch_size(exception):
                    bs //= 2
                    gc.collect()
                    torch.cuda.empty_cache()
                else:
                    raise
            except Exception as exception:  # pylint: disable=broad-except
                # catches the torch.cuda.OutOfMemoryError
                if bs > 1 and should_reduce_batch_size(exception):
                    bs //= 2
                    gc.collect()
                    torch.cuda.empty_cache()
                else:
                    raise
            else:
                break

    def fit(self) -> None:
        """Where the ✨️magic✨️ happens..."""
        try:
            self._fit()
            if self.args.rank == 0:
                self.dashboard_logger.finish()
        except KeyboardInterrupt:
            logger.info(" > Keyboard interrupt detected.")
            if self.config.save_on_interrupt:
                logger.info(" > Saving model before exiting...")
                # save the model on keyboard interrupt
                self.save_checkpoint()
                # update the training dashboard logger
                self.update_training_dashboard_logger()
            # call the keyboard interrupt callback
            self.callbacks.on_keyboard_interrupt(self)
            # if the output folder is empty remove the run.
            remove_experiment_folder(self.output_path)
            # clear the DDP processes
            if self.num_gpus > 1:
                dist.destroy_process_group()
            # finish the wandb run and sync data
            if self.args.rank == 0:
                self.dashboard_logger.finish()
            # stop without error signal
            try:
                sys.exit(130)
            except SystemExit:
                os._exit(130)  # pylint: disable=protected-access
        except BaseException:  # pylint: disable=broad-except
            remove_experiment_folder(self.output_path)
            traceback.print_exc()
            sys.exit(1)

    def profile_fit(
        self, torch_profiler: torch.profiler.profile, epochs: int | None = None, small_run: int | None = None
    ) -> torch.profiler.profile:
        """Run training under the torch profiler.

        Example::
            Run torch profiler to profile CPU, GPU and memory usage with Tensorboard logging.

            >>> import torch
            >>> profiler = torch.profiler.profile(
            >>>        activities=[
            >>>         torch.profiler.ProfilerActivity.CPU,
            >>>         torch.profiler.ProfilerActivity.CUDA,
            >>>     ],
            >>>     schedule=torch.profiler.schedule(wait=1, warmup=1, active=3, repeat=2),
            >>>     on_trace_ready=torch.profiler.tensorboard_trace_handler("./profiler/"),
            >>>     record_shapes=True,
            >>>     profile_memory=True,
            >>>     with_stack=True,
            >>> )
            >>> prof = trainer.profile_fit(profiler, epochs=1, small_run=64)
        """
        self.dashboard_logger = DummyLogger()
        # train the model for a custom number of epochs
        if epochs:
            self.config.epochs = epochs
        # use a smaller set of training samples for profiling
        if small_run:
            self.setup_small_run(small_run)
        # run profiler
        self.config.run_eval = False
        self.config.test_delay_epochs = 9999999
        # set a callback to progress the profiler
        self.callbacks_on_train_step_end = [  # pylint: disable=attribute-defined-outside-init
            lambda trainer: trainer.torch_profiler.step()
        ]
        # set the profiler to access in the Trainer
        self.torch_profiler = torch_profiler  # pylint: disable=attribute-defined-outside-init
        # set logger output for Tensorboard
        # self.torch_profiler.on_trace_ready = torch.profiler.tensorboard_trace_handler(self.output_path)
        self.torch_profiler.start()
        self.fit()
        self.torch_profiler.stop()
        return self.torch_profiler

    @rank_zero_only
    def save_best_model(self) -> None:
        """Save the best model. It only saves if the current target loss is smaller then the previous."""
        eval_loss = self._pick_target_avg_loss(self.keep_avg_eval)
        train_loss = self._pick_target_avg_loss(self.keep_avg_train) or float("inf")

        # save the model and update the best_loss
        self.best_loss = save_best_model(
            {"train_loss": train_loss, "eval_loss": eval_loss},
            self.best_loss,
            self.config,
            self._get_model(),
            self.output_path,
            current_step=self.total_steps_done,
            epoch=self.epochs_done,
            optimizer=self.optimizer,
            scheduler=self.scheduler,
            scaler=self.scaler if self.use_amp_scaler else None,
            keep_all_best=self.config.save_all_best,
            keep_after=self.config.save_best_after,
            save_func=self.dashboard_logger.save_model,
        )

    @rank_zero_only
    def save_checkpoint(self) -> None:
        """Save the current model checkpoint."""
        eval_loss = self._pick_target_avg_loss(self.keep_avg_eval)
        train_loss = self._pick_target_avg_loss(self.keep_avg_train)

        save_checkpoint(
            self.config,
            self._get_model(),
            self.output_path,
            current_step=self.total_steps_done,
            epoch=self.epochs_done,
            optimizer=self.optimizer,
            scheduler=self.scheduler,
            scaler=self.scaler if self.use_amp_scaler else None,
            model_loss={"train_loss": train_loss, "eval_loss": eval_loss},
            save_n_checkpoints=self.config.save_n_checkpoints,
            save_func=self.dashboard_logger.save_model,
        )

    @rank_zero_only
    def update_training_dashboard_logger(
        self, batch: dict[str, Any] | list[Any] | None = None, outputs: dict[str, Any] | None = None
    ) -> None:
        aliases = [
            f"epoch-{self.epochs_done}",
            f"step-{self.total_steps_done}",
        ]
        self.dashboard_logger.add_artifact(
            file_or_dir=self.output_path, name="checkpoint", artifact_type="model", aliases=aliases
        )

        # training visualizations
        if batch is not None and outputs is not None:
            model = self._get_model()
            with suppress(NotImplementedError):
                model.train_log(
                    batch,
                    outputs,
                    self.dashboard_logger,
                    self.training_assets,
                    self.total_steps_done,
                )

    #####################
    # GET FUNCTIONS
    #####################

    @staticmethod
    def get_optimizer(model: TrainerModel, config: TrainerConfig) -> ValueListDict[torch.optim.Optimizer]:
        """Return the optimizer.

        From the model if model implements `get_optimizer()` else
        check the optimizer parameters in the config and try initiating the optimizer.

        Args:
            model (TrainerModel): Training model.
            config (TrainerConfig): Training configuration.

        Returns:
            Union[torch.optim.Optimizer, List]: A optimizer or a list of optimizers. GAN models define a list.
        """
        try:
            return model.get_optimizer()
        except NotImplementedError as e:
            if isinstance(config.optimizer, list):
                optimizers = []
                for i, optimizer_name in enumerate(config.optimizer):
                    optimizer_params = {} if config.optimizer_params is None else config.optimizer_params[i]  # type: ignore[index]
                    optimizers.append(get_optimizer(optimizer_name, optimizer_params, config.lr, model))  # type: ignore[arg-type]
                return optimizers
            if config.optimizer is None:
                msg = "No name specified in `optimizer`"
                raise ValueError(msg) from e
            optimizer_name = config.optimizer
            optimizer_params = {} if config.optimizer_params is None else config.optimizer_params
            return get_optimizer(optimizer_name, optimizer_params, config.lr, model)  # type: ignore[arg-type]

    @staticmethod
    def get_lr(model: TrainerModel, config: TrainerConfig) -> float | list[float] | dict[str, float]:
        """Set the initial learning rate.

        According to the model if model implements `get_lr()` else try setting
        the learning rate from the config.

        Args:
            model (TrainerModel): Training model.
            config (TrainerConfig): Training configuration.

        Returns:
            Union[float, List[float]]: A single learning rate or a list of learning rates, one for each optimzier.
        """
        try:
            return model.get_lr()
        except NotImplementedError:
            return config.lr

    @staticmethod
    def get_scheduler(
        model: TrainerModel,
        config: TrainerConfig,
        optimizer: torch.optim.Optimizer | list[torch.optim.Optimizer] | dict[str, torch.optim.Optimizer],
    ) -> ValueListDict[LRScheduler] | None:
        """Return the scheduler.

        From the model if model implements `get_scheduler()` else
        check the config and try initiating the scheduler.

        Args:
            model (TrainerModel): Training model.
            config (TrainerConfig): Training configuration.

        Returns:
            Union[torch.optim.Optimizer, List, Dict]: A scheduler or a list of schedulers, one for each optimizer.
        """
        try:
            return model.get_scheduler(optimizer)
        except NotImplementedError:
            lr_scheduler = config.lr_scheduler
            lr_scheduler_params = config.lr_scheduler_params
            return get_scheduler(lr_scheduler, lr_scheduler_params, optimizer)  # type: ignore[arg-type]

    @staticmethod
    def get_criterion(model: TrainerModel) -> nn.Module | list[nn.Module]:
        """Receive the criterion from the model. Model must implement `get_criterion()`.

        Args:
            model (TrainerModel): Training model.

        Returns:
            nn.Module: Criterion layer.
        """
        return model.get_criterion()

    ####################
    # HELPER FUNCTIONS
    ####################

    @staticmethod
    def _detach_loss_dict(loss_dict: dict[str, Any]) -> dict[str, Any]:
        """Detach loss values from autograp.

        Args:
            loss_dict (Dict): losses.

        Returns:
            Dict: losses detached from autograph.
        """
        loss_dict_detached = {}
        for key, value in loss_dict.items():
            if isinstance(value, (int | float)):
                loss_dict_detached[key] = value
            else:
                loss_dict_detached[key] = value.detach().cpu().item()
        return loss_dict_detached

    def _pick_target_avg_loss(self, keep_avg_target: KeepAverage | None) -> float | None:
        """Pick the target loss to compare models."""
        # if the keep_avg_target is None or empty return None
        if keep_avg_target is None or len(list(keep_avg_target.avg_values.keys())) == 0:
            return None

        # return if target loss defined in the model config
        # if not available in Dict use loss_1 as by default loss
        if "target_loss" in self.config and self.config.target_loss:
            if f"avg_{self.config.target_loss}" in keep_avg_target.avg_values:
                return keep_avg_target[f"avg_{self.config.target_loss}"]

            msg = " [!] Target loss not found in the keep_avg_target. You might be exiting the training loop before it is computed or set the target_loss in the model config incorrectly."
            raise ValueError(msg)

        # take the average of loss_{optimizer_idx} as the target loss when there are multiple optimizers
        if isinstance(self.optimizer, list):
            target_avg_loss = 0.0
            for idx in range(len(self.optimizer)):
                if f"avg_loss_{idx}" in keep_avg_target.avg_values:
                    target_avg_loss += keep_avg_target[f"avg_loss_{idx}"]
            target_avg_loss /= len(self.optimizer)
        else:
            target_avg_loss = keep_avg_target.avg_values.get("avg_loss", 0)
        return target_avg_loss

    def _setup_logger_config(self, log_file: str) -> None:
        """Set up the logger based on the process rank in DDP."""
        logger_new = logging.getLogger("trainer")
        handler = logging.FileHandler(log_file, mode="a")
        fmt = logging.Formatter("")
        handler.setFormatter(fmt)
        logger_new.addHandler(handler)

        # only log to a file if rank > 0 in DDP
        if self.args.rank > 0:
            logger_new.handlers = [h for h in logger_new.handlers if not isinstance(h, logging.StreamHandler)]
