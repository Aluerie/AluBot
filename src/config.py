from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types_.config import Config

__all__ = ("config",)


with Path("config.toml").open("rb") as fp:
    config: Config = tomllib.load(fp)  # pyright: ignore[reportAssignmentType]
