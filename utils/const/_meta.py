from __future__ import annotations

from typing import Any, NoReturn

__all__ = ("CONSTANTS",)


class ConstantsMeta(type):
    def __setattr__(self, attr: str, nv: Any) -> NoReturn:
        msg = f"Constant <{attr}> cannot be assigned to."
        raise RuntimeError(msg)

    def __delattr__(self, attr: str) -> NoReturn:
        msg = f"Constant <{attr}> cannot be deleted."
        raise RuntimeError(msg)


class CONSTANTS(metaclass=ConstantsMeta):
    pass
