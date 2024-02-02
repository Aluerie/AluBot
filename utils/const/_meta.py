from __future__ import annotations

from typing import Any, NoReturn, override

__all__ = ("CONSTANTS",)


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
