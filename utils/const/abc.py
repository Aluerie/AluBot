from __future__ import annotations

from typing import Any, NoReturn, override

__all__ = (
    "ASSETS_IMAGES",
    "CONSTANTS",
    "RAW_GITHUB_IMAGES",
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
    """CONSTANTS.

    Attributes of this class are not allowed to be changed or deleted during runtime.
    """


ASSETS_IMAGES = "./assets/images/"
RAW_GITHUB_IMAGES = "https://raw.githubusercontent.com/Aluerie/AluBot/main/assets/images/"

"""
Apparently this does not work because StrEnum is a Final therefore no subclasses.

class ImageAsset(StrEnum):
    @override
    def __str__(self) -> str:
        "Relative location compared to the workplace directory, i.e. `./assets/images/logo/dota_white.png`"
        return f"./assets/images/{self.value}"

    @property
    def url(self) -> str:
        return f"https://raw.githubusercontent.com/Aluerie/AluBot/main/assets/images/{self.value}"
"""
