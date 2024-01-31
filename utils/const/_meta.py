from __future__ import annotations

from typing import Any, NoReturn

__all__ = ("CONSTANTS",)


class ConstantsMeta(type):
    def __setattr__(self, attr: str, nv: Any) -> NoReturn:
        raise RuntimeError(f"Constant <{attr}> cannot be assigned to.")

    def __delattr__(self, attr: str) -> NoReturn:
        raise RuntimeError(f"Constant <{attr}> cannot be deleted.")


class CONSTANTS(metaclass=ConstantsMeta):
    pass
