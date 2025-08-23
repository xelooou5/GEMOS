import datetime
import json
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import fsspec
import torch
from coqpit import Coqpit
from torch.optim.optimizer import StateDict
from torch.types import Storage

from trainer._types import LossDict, LRScheduler, ValueListDict
from trainer.generic_utils import is_pytorch_at_least_2_4, map_value_list_dict
from trainer.logger import logger
from trainer.model import TrainerModel

# `torch.serialization.add_safe_globals` is needed for weights_only=True to work
# with all Coqui models and only available from Pytorch >=2.4
_WEIGHTS_ONLY = is_pytorch_at_least_2_4()


def get_user_data_dir(appname: str) -> Path:
    TTS_HOME = os.environ.get("TTS_HOME")
    XDG_DATA_HOME = os.environ.get("XDG_DATA_HOME")
    if TTS_HOME is not None:
        ans = Path(TTS_HOME).expanduser().resolve(strict=False)
    elif XDG_DATA_HOME is not None:
        ans = Path(XDG_DATA_HOME).expanduser().resolve(strict=False)
    elif sys.platform == "win32":
        import winreg  # pylint: disable=import-outside-toplevel

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        dir_, _ = winreg.QueryValueEx(key, "Local AppData")
        ans = Path(dir_).resolve(strict=False)
    elif sys.platform == "darwin":
        ans = Path("~/Library/Application Support/").expanduser()
    else:
        ans = Path.home().joinpath(".local/share")
    return ans.joinpath(appname)


def copy_model_files(config: Coqpit, out_path: str | os.PathLike[Any], new_fields: dict[str, Any]) -> None:
    """Copy config.json and other model files to training folder and add new fields.

    Args:
        config (Coqpit): Coqpit config defining the training run.
        out_path (str): output path to copy the file.
        new_fields (dict): new fileds to be added or edited
            in the config file.
    """
    copy_config_path = os.path.join(out_path, "config.json")
    # add extra information fields
    new_config = {**config.to_dict(), **new_fields}
    # TODO: Revert to config.save_json() once Coqpit supports arbitrary paths.
    with fsspec.open(copy_config_path, "w", encoding="utf8") as f:
        json.dump(new_config, f, indent=4)


def load_fsspec(
    path: str | os.PathLike[Any],
    map_location: str | Callable[[Storage, str], Storage] | torch.device | dict[str, str] | None = None,
    *,
    cache: bool = True,
    **kwargs: Any,
) -> Any:
    """Like torch.load but can load from other locations (e.g. s3:// , gs://).

    Args:
        path: Any path or url supported by fsspec.
        map_location: torch.device or str.
        cache: If True, cache a remote file locally for subsequent calls. It is cached under `get_user_data_dir()/trainer_cache`. Defaults to True.
        **kwargs: Keyword arguments forwarded to torch.load.

    Returns:
        Object stored in path.
    """
    is_local = Path(path).exists()
    if cache and not is_local:
        with fsspec.open(
            f"filecache::{path}",
            filecache={"cache_storage": str(get_user_data_dir("tts_cache"))},
            mode="rb",
        ) as f:
            return torch.load(f, map_location=map_location, weights_only=_WEIGHTS_ONLY, **kwargs)
    else:
        with fsspec.open(str(path), "rb") as f:
            return torch.load(f, map_location=map_location, weights_only=_WEIGHTS_ONLY, **kwargs)


def load_checkpoint(
    model: torch.nn.Module,
    checkpoint_path: str | os.PathLike[Any],
    *,
    use_cuda: bool = False,
    eval: bool = False,
    cache: bool = False,
) -> tuple[torch.nn.Module, Any]:  # pylint: disable=redefined-builtin
    state = load_fsspec(checkpoint_path, map_location=torch.device("cpu"), cache=cache)
    model.load_state_dict(state["model"])
    if use_cuda:
        model.cuda()
    if eval:
        model.eval()
    return model, state


def save_fsspec(state: Any, path: str | os.PathLike[Any], **kwargs: Any) -> None:
    """Like torch.save but can save to other locations (e.g. s3:// , gs://).

    Args:
        state: State object to save
        path: Any path or url supported by fsspec.
        **kwargs: Keyword arguments forwarded to torch.save.
    """
    with fsspec.open(str(path), "wb") as f:
        torch.save(state, f, **kwargs)


def save_model(
    config: dict[str, Any] | Coqpit,
    model: TrainerModel,
    output_path: str | os.PathLike[Any],
    *,
    current_step: int,
    epoch: int,
    optimizer: ValueListDict[torch.optim.Optimizer] | None = None,
    scheduler: ValueListDict[LRScheduler] | None = None,
    scaler: "torch.GradScaler | None" = None,
    save_func: Callable[[Any, str | os.PathLike[Any]], None] | None = None,
    **kwargs: Any,
) -> None:
    model_state = model.state_dict()
    optimizer_state: ValueListDict[StateDict] | None = None
    if optimizer is not None:
        optimizer_state = map_value_list_dict(optimizer, lambda o: o.state_dict())

    scheduler_state: ValueListDict[StateDict] | None = None
    if scheduler is not None:
        scheduler_state = map_value_list_dict(scheduler, lambda s: s.state_dict())

    scaler_state: StateDict | list[StateDict] | None = None
    if isinstance(scaler, list):
        scaler_state = [s.state_dict() for s in scaler]
    else:
        scaler_state = scaler.state_dict() if scaler is not None else None

    if isinstance(config, Coqpit):
        config = config.to_dict()

    state = {
        "config": config,
        "model": model_state,
        "optimizer": optimizer_state,
        "scheduler": scheduler_state,
        "scaler": scaler_state,
        "step": current_step,
        "epoch": epoch,
        "date": datetime.date.today().strftime("%B %d, %Y"),
    }
    state.update(kwargs)
    if save_func is not None:
        save_func(state, output_path)
    else:
        save_fsspec(state, output_path)


def save_checkpoint(
    config: dict[str, Any] | Coqpit,
    model: TrainerModel,
    output_folder: str | os.PathLike[Any],
    *,
    current_step: int,
    epoch: int,
    optimizer: ValueListDict[torch.optim.Optimizer] | None = None,
    scheduler: ValueListDict[LRScheduler] | None = None,
    scaler: "torch.GradScaler | None" = None,
    save_n_checkpoints: int | None = None,
    save_func: Callable[[Any, str | os.PathLike[Any]], None] | None = None,
    **kwargs: Any,
) -> None:
    file_name = f"checkpoint_{current_step}.pth"
    checkpoint_path = os.path.join(output_folder, file_name)

    logger.info("\n > CHECKPOINT : %s", checkpoint_path)
    save_model(
        config,
        model,
        checkpoint_path,
        current_step=current_step,
        epoch=epoch,
        optimizer=optimizer,
        scheduler=scheduler,
        scaler=scaler,
        save_func=save_func,
        **kwargs,
    )
    if save_n_checkpoints is not None:
        keep_n_checkpoints(output_folder, save_n_checkpoints)


def save_best_model(
    current_loss: LossDict | float,
    best_loss: LossDict | float,
    config: dict[str, Any] | Coqpit,
    model: TrainerModel,
    out_path: str | os.PathLike[Any],
    *,
    current_step: int,
    epoch: int,
    optimizer: ValueListDict[torch.optim.Optimizer] | None = None,
    scheduler: ValueListDict[LRScheduler] | None = None,
    scaler: "torch.GradScaler | None" = None,
    keep_all_best: bool = False,
    keep_after: int = 0,
    save_func: Callable[[Any, str | os.PathLike[Any]], None] | None = None,
    **kwargs: Any,
) -> LossDict | float:
    if isinstance(current_loss, dict) and isinstance(best_loss, dict):
        if current_loss["eval_loss"] is not None and best_loss["eval_loss"] is not None:
            is_save_model = current_loss["eval_loss"] < best_loss["eval_loss"]
        else:
            is_save_model = current_loss["train_loss"] < best_loss["train_loss"]
    else:
        assert isinstance(current_loss, float) and isinstance(best_loss, float)
        is_save_model = current_loss < best_loss

    is_save_model = is_save_model and current_step > keep_after

    if is_save_model:
        best_model_name = f"best_model_{current_step}.pth"
        checkpoint_path = os.path.join(out_path, best_model_name)
        logger.info(" > BEST MODEL : %s", checkpoint_path)
        save_model(
            config,
            model,
            checkpoint_path,
            current_step=current_step,
            epoch=epoch,
            optimizer=optimizer,
            scheduler=scheduler,
            scaler=scaler,
            model_loss=current_loss,
            save_func=save_func,
            **kwargs,
        )
        fs = fsspec.get_mapper(str(out_path)).fs
        # only delete previous if current is saved successfully
        if not keep_all_best or (current_step < keep_after):
            model_names = fs.glob(os.path.join(out_path, "best_model*.pth"))
            for model_name in model_names:
                if os.path.basename(model_name) != best_model_name:
                    fs.rm(model_name)
        # create a shortcut which always points to the currently best model
        shortcut_name = "best_model.pth"
        shortcut_path = os.path.join(out_path, shortcut_name)
        fs.copy(checkpoint_path, shortcut_path)
        best_loss = current_loss
    return best_loss


def get_last_checkpoint(path: str | os.PathLike[Any]) -> tuple[str, str]:
    """Get latest checkpoint or/and best model in path.

    It is based on globbing for `*.pth` and the RegEx
    `(checkpoint|best_model)_([0-9]+)`.

    Args:
        path: Path to files to be compared.

    Raises:
        ValueError: If no checkpoint or best_model files are found.

    Returns:
        Path to the last checkpoint
        Path to best checkpoint
    """
    path = str(path)
    fs = fsspec.get_mapper(path).fs
    file_names = fs.glob(os.path.join(path, "*.pth"))
    scheme = urlparse(path).scheme
    if scheme and path.startswith(scheme + "://"):
        # scheme is not preserved in fs.glob, add it
        # back if it exists on the path
        file_names = [scheme + "://" + file_name for file_name in file_names]
    last_models = {}
    last_model_nums: dict[str, int] = {}
    for key in ["checkpoint", "best_model"]:
        last_model_num = None
        last_model = None
        # pass all the checkpoint files and find
        # the one with the largest model number suffix.
        for file_name in file_names:
            match = re.search(f"{key}_([0-9]+)", file_name)
            if match is not None:
                model_num = int(match.groups()[0])
                if last_model_num is None or model_num > last_model_num:
                    last_model_num = model_num
                    last_model = file_name

        # if there is no checkpoint found above
        # find the checkpoint with the latest
        # modification date.
        key_file_names = [fn for fn in file_names if key in fn]
        if last_model is None and len(key_file_names) > 0:
            last_model = max(key_file_names, key=os.path.getctime)
            last_model_num = load_fsspec(last_model)["step"]

        if last_model is not None and last_model_num is not None:
            last_models[key] = last_model
            last_model_nums[key] = last_model_num

    # check what models were found
    if not last_models:
        msg = f"No models found in continue path {path}!"
        raise ValueError(msg)
    if "checkpoint" not in last_models:  # no checkpoint just best model
        last_models["checkpoint"] = last_models["best_model"]
    elif "best_model" not in last_models:  # no best model
        # this shouldn't happen, but let's handle it just in case
        last_models["best_model"] = last_models["checkpoint"]
    # finally check if last best model is more recent than checkpoint
    elif last_model_nums["best_model"] > last_model_nums["checkpoint"]:
        last_models["checkpoint"] = last_models["best_model"]

    return last_models["checkpoint"], last_models["best_model"]


def keep_n_checkpoints(path: str | os.PathLike[Any], n: int) -> None:
    """Keep only the last n checkpoints in path.

    Args:
        path: Path to files to be compared.
        n: Number of checkpoints to keep.
    """
    fs = fsspec.get_mapper(str(path)).fs
    file_names = sort_checkpoints(path, "checkpoint")
    if len(file_names) > n:
        for file_name in file_names[:-n]:
            fs.rm(file_name)


def sort_checkpoints(
    output_path: str | os.PathLike[Any], checkpoint_prefix: str, *, use_mtime: bool = False
) -> list[str]:
    """Sort checkpoint paths based on the checkpoint step number.

    Args:
        output_path: Path to directory containing checkpoints.
        checkpoint_prefix (str): Prefix of the checkpoint files.
        use_mtime (bool): If True, use modification dates to determine checkpoint order.
    """
    ordering_and_checkpoint_path = []

    output_path = str(output_path)
    fs = fsspec.get_mapper(output_path).fs
    glob_checkpoints = fs.glob(os.path.join(output_path, f"{checkpoint_prefix}_*"))
    scheme = urlparse(output_path).scheme
    if scheme and output_path.startswith(scheme + "://"):
        # scheme is not preserved in fs.glob, add it back if it exists on the path
        glob_checkpoints = [scheme + "://" + file_name for file_name in glob_checkpoints]

    for path in glob_checkpoints:
        if use_mtime:
            ordering_and_checkpoint_path.append((os.path.getmtime(path), path))
        else:
            regex_match = re.match(f".*{checkpoint_prefix}_([0-9]+)", path)
            if regex_match is not None and regex_match.groups() is not None:
                ordering_and_checkpoint_path.append((int(regex_match.groups()[0]), path))

    return [checkpoint[1] for checkpoint in sorted(ordering_and_checkpoint_path)]
