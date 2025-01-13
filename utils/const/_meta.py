from __future__ import annotations

from enum import StrEnum
from typing import Any, NoReturn, override

__all__ = (
    "CONSTANTS",
    "ImageAsset",
)


class ConstantsMeta(type):
    @override
    def __setattr__(cls, attr: str, nv: Any) -> NoReturn:
        msg = f"Constant <{attr}> cannot be assigned to."
        raise RuntimeError(msg)

    @override
    def __delattr__(cls, attr: str) -> NoReturn:
        msg = f"Constant <{attr}> cannot be deleted."
        raise RuntimeError(msg)


class CONSTANTS(metaclass=ConstantsMeta):
    pass


class ImageAsset(StrEnum):
    @override
    def __str__(self) -> str:
        """Relative location compared to the workplace directory, i.e. `./assets/images/logo/dota_white.png`"""
        return f"./assets/images/{self.value}"

    @property
    def url(self) -> str:
        return f"https://raw.githubusercontent.com/Aluerie/AluBot/main/assets/images/{self.value}"
