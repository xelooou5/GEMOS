from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import torch
from torch import nn

from trainer._types import ValueListDict

if TYPE_CHECKING:
    from trainer.trainer import Trainer


class TrainerModel(ABC, nn.Module):
    """Abstract 🐸TTS class. Every new 🐸TTS model must inherit this."""

    @abstractmethod
    def forward(
        self, input: torch.Tensor, *args: Any, aux_input: dict[str, Any] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Forward ... for the model mainly used in training.

        You can be flexible here and use different number of arguments and argument names since it is intended to be
        used by `train_step()` without exposing it out of the model.

        Args:
            input (torch.Tensor): Input tensor.
            aux_input (Dict): Auxiliary model inputs like embeddings, durations or any other sorts of inputs.

        Returns:
            Dict: Model outputs. Main model output must be named as "model_outputs".
        """
        if aux_input is None:
            aux_input = {}
        outputs_dict = {"model_outputs": None}
        ...
        return outputs_dict

    def format_batch(self, batch: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
        """Format batch returned by the data loader before sending it to the model.

        If not implemented, model uses the batch as is.
        Can be used for data augmentation, feature ectraction, etc.
        """
        return batch

    def format_batch_on_device(self, batch: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
        """Format batch on device before sending it to the model.

        If not implemented, model uses the batch as is.
        Can be used for data augmentation, feature ectraction, etc.`
        """
        return batch

    def train_step(self, *args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """Perform a single training step. Run the model forward ... and compute losses.

        Args:
            batch (Dict): Input tensors.
            criterion (nn.Module): Loss layer designed for the model.
            optimizer_idx (int): Index of optimizer to use. 0 for the generator and 1 for the discriminator networks.

        Returns:
            Tuple[Dict, Dict]: Model outputs and computed losses.
        """
        msg = " [!] `train_step()` is not implemented."
        raise NotImplementedError(msg)

    def train_log(self, *args: Any, **kwargs: Any) -> None:
        """Create visualizations and waveform examples for training.

        For example, here you can plot spectrograms and generate sample sample waveforms from these spectrograms to
        be projected onto Tensorboard.

        Args:
            batch (Dict): Model inputs used at the previous training step.
            outputs (Dict): Model outputs generated at the previoud training step.
            logger (Logger): Logger instance to log training plots.
            assets (Dict): Assets to be used for logging from the trainer's closure.
            steps (int): Number of training steps taken so far.

        Returns:
            Tuple[Dict, np.ndarray]: training plots and output waveform.
        """
        msg = " [!] `train_log()` is not implemented."
        raise NotImplementedError(msg)

    @torch.inference_mode()
    def eval_step(self, *args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """Perform a single evaluation step.

        Run the model forward ... and compute losses. In most cases, you can
        call `train_step()` with no changes.

        Args:
            batch (Dict): Input tensors.
            criterion (nn.Module): Loss layer designed for the model.
            optimizer_idx (int): Index of optimizer to use. 0 for the generator and 1 for the discriminator networks.

        Returns:
            Tuple[Dict, Dict]: Model ouputs and computed losses.
        """
        msg = " [!] `eval_step()` is not implemented."
        raise NotImplementedError(msg)

    def eval_log(self, *args: Any, **kwargs: Any) -> None:
        """The same as `train_log()`."""
        msg = " [!] `eval_log()` is not implemented."
        raise NotImplementedError(msg)

    @abstractmethod
    def get_data_loader(*args: Any, **kwargs: Any) -> torch.utils.data.DataLoader[Any]:
        """Get data loader for the model.

        Args:
            config (TrainerConfig): Configuration object.
            assets (Dict): Additional assets to be used for data loading.
            is_eval (bool): If True, returns evaluation data loader.
            samples (Union[List[Dict], List[List]]): List of samples to be used for data loading.
            verbose (bool): If True, prints data loading information.
            num_gpus (int): Number of GPUs used for training.
            rank (int): Rank of the current GPU.

        Returns:
            torch.utils.data.DataLoader: Data loader for the model.
        """
        ...
        msg = " [!] `get_data_loader()` is not implemented."
        raise NotImplementedError(msg)

    def get_train_data_loader(*args: Any, **kwargs: Any) -> torch.utils.data.DataLoader[Any]:
        raise NotImplementedError

    def get_eval_data_loader(*args: Any, **kwargs: Any) -> torch.utils.data.DataLoader[Any]:
        raise NotImplementedError

    def get_test_data_loader(*args: Any, **kwargs: Any) -> torch.utils.data.DataLoader[Any]:
        raise NotImplementedError

    def test_run(self, *args: Any, **kwargs: Any):
        raise NotImplementedError

    def test(self, assets: dict[str, Any], data_loader: torch.utils.data.DataLoader[Any], outputs: Any | None = None):
        raise NotImplementedError

    def test_log(self, *args: Any, **kwargs: Any):
        raise NotImplementedError

    def init_for_training(self) -> None:
        """Initialize model for training."""

    def optimize(self, *args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """Model specific optimization step that must perform the following steps.

            1. Forward pass
            2. Compute loss
            3. Backward pass
            4. Update weights.

        Use `self.scaled_backward()` instead of `loss.backward()` to be able to use Mixed Precision Training.

        Args:
            batch (Dict): Input tensors.
            trainer (Trainer): Trainer instance to be able to access the training closure.

        Returns:
            Tuple[Dict, Dict, float]: Model outputs, loss dictionary.
        """
        msg = " [!] `optimize()` is not implemented."
        raise NotImplementedError(msg)

    def scaled_backward(
        self,
        loss: torch.Tensor,
        trainer: "Trainer",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Backward pass with gradient scaling for custom `optimize` calls.

        Args:
            loss (torch.Tensor): Loss to be backpropagated.
            trainer (Trainer): Trainer instance to be able to access the training closure.
        """
        if trainer.use_amp_scaler:
            if trainer.scaler is not None:
                # model optimizer step in mixed precision mode
                trainer.scaler.scale(loss).backward()
        else:
            # main model optimizer step
            loss.backward()

    def get_optimizer(self) -> torch.optim.Optimizer | list[torch.optim.Optimizer]:
        """Setup an return optimizer or optimizers."""
        raise NotImplementedError

    def get_lr(self) -> float | list[float]:
        """Return learning rate(s).

        Returns:
            Union[float, List[float]]: Model's initial learning rates.
        """
        raise NotImplementedError

    def get_scheduler(
        self, optimizer: torch.optim.Optimizer | list[torch.optim.Optimizer] | dict[str, torch.optim.Optimizer]
    ):
        raise NotImplementedError

    def get_criterion(self) -> nn.Module | list[nn.Module]:
        """Return model criterion."""
        msg = "`get_criterion` is not implemented."
        raise NotImplementedError(msg)

    ## Callbacks
    def on_init_start(self, trainer: "Trainer") -> None: ...

    def on_init_end(self, trainer: "Trainer") -> None: ...

    def on_epoch_start(self, trainer: "Trainer") -> None: ...

    def on_epoch_end(self, trainer: "Trainer") -> None: ...

    def on_train_epoch_start(self, trainer: "Trainer") -> None: ...

    def on_train_epoch_end(self, trainer: "Trainer") -> None: ...

    @staticmethod
    def before_backward_pass(loss_dict: dict[str, Any], optimizer: ValueListDict[torch.optim.Optimizer]) -> None: ...

    @staticmethod
    def before_gradient_clipping() -> None: ...

    def on_train_step_start(self, trainer: "Trainer") -> None: ...

    def on_train_step_end(self, trainer: "Trainer") -> None: ...

    def on_keyboard_interrupt(self, trainer: "Trainer") -> None: ...
