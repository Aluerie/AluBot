from __future__ import annotations

import asyncio
import enum
import logging
import time
from collections import UserDict
from functools import wraps
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, override

from lru import LRU

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator, MutableMapping


R = TypeVar("R")


# Can't use ParamSpec due to https://github.com/python/typing/discussions/946
class CacheProtocol(Protocol[R]):
    cache: MutableMapping[str, asyncio.Task[R]]

    def __call__(self, *args: Any, **kwds: Any) -> asyncio.Task[R]: ...

    def get_key(self, *args: Any, **kwargs: Any) -> str: ...

    def invalidate(self, *args: Any, **kwargs: Any) -> bool: ...

    def invalidate_containing(self, key: str) -> None: ...

    def get_stats(self) -> tuple[int, int]: ...


class ExpiringCache(UserDict[Any, Any]):
    def __init__(self, seconds: float) -> None:
        self.__ttl: float = seconds
        super().__init__()

    def __verify_cache_integrity(self) -> None:
        # Have to do this in two steps...
        current_time = time.monotonic()
        to_remove = [k for (k, (_, t)) in super().items() if current_time > (t + self.__ttl)]
        for k in to_remove:
            del self[k]

    @override
    def __contains__(self, key: str) -> bool:
        self.__verify_cache_integrity()
        return super().__contains__(key)

    @override
    def __getitem__(self, key: str) -> Any:
        self.__verify_cache_integrity()
        v, _ = super().__getitem__(key)
        return v

    @override
    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, (value, time.monotonic()))

    @override
    def get(self, key: str, default: Any = None) -> Any:
        self.__verify_cache_integrity()
        v = super().get(key, default)
        return default if v is default else v[0]

    @override
    def values(self) -> Generator[Any, None, None]:
        return (x[0] for x in super().values())  # map(lambda x: x[0], super().values())
        # https://docs.astral.sh/ruff/rules/unnecessary-map/

    @override
    def items(self) -> Generator[tuple[Any, Any], None, None]:
        """Generator `for key, value in items()` iterator.

        Note that this function should be used like this:
        >>> for (key, value) in self.items():
        Whereas the `super().items()` function should be used when we need ttl:
        >>> for (key, (value, ttl)) in super().items():
        """
        return ((x[0], x[1][0]) for x in super().items())  # map(lambda x: (x[0], x[1][0]), super().items())


class Strategy(enum.Enum):
    lru = 1
    raw = 2
    timed = 3


def cache(
    maxsize: int = 128,
    strategy: Strategy = Strategy.lru,
    *,
    ignore_kwargs: bool = False,
) -> Callable[[Callable[..., Coroutine[Any, Any, R]]], CacheProtocol[R]]:
    def decorator(func: Callable[..., Coroutine[Any, Any, R]]) -> CacheProtocol[R]:
        if strategy is Strategy.lru:
            internal_cache = LRU(maxsize)
            stats = internal_cache.get_stats
        elif strategy is Strategy.raw:
            internal_cache = {}
            stats = lambda: (0, 0)  # noqa: E731
        elif strategy is Strategy.timed:
            internal_cache = ExpiringCache(seconds=maxsize)
            stats = lambda: (0, 0)  # noqa: E731

        def _make_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
            # this is a bit of a cluster fuck
            # we do care what 'self' parameter is when we __repr__ it
            def _true_repr(o: Any) -> str:
                if o.__class__.__repr__ is object.__repr__:
                    return f"<{o.__class__.__module__}.{o.__class__.__name__}>"
                return repr(o)

            key = [f"{func.__module__}.{func.__name__}"]
            key.extend(_true_repr(o) for o in args)
            if not ignore_kwargs:
                for k, v in kwargs.items():
                    # note: this only really works for this use case in particular
                    # I want to pass asyncpg.Connection objects to the parameters
                    # however, they use default __repr__ and I do not care what
                    # connection is passed in, so I needed a bypass.
                    if k in {"connection", "pool"}:
                        continue

                    key.extend((_true_repr(k), _true_repr(v)))

            return ":".join(key)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> asyncio.Task[Any]:  # is it proper type?
            key = _make_key(args, kwargs)
            try:
                task = internal_cache[key]
            except KeyError:
                internal_cache[key] = task = asyncio.create_task(func(*args, **kwargs))
                return task
            else:
                return task

        def _invalidate(*args: Any, **kwargs: Any) -> bool:
            try:
                del internal_cache[_make_key(args, kwargs)]
            except KeyError:
                return False
            else:
                return True

        def _invalidate_containing(key: str) -> None:
            to_remove = [k for k in internal_cache if key in k]
            for k in to_remove:
                try:
                    del internal_cache[k]
                except KeyError:
                    continue

        # TODO: investigate those "type: ignore"
        wrapper.cache = internal_cache  # type:ignore[reportAttributeAccessIssue]
        wrapper.get_key = lambda *args, **kwargs: _make_key(args, kwargs)  # type: ignore[reportAttributeAccessIssue]
        wrapper.invalidate = _invalidate  # type: ignore[reportAttributeAccessIssue]
        wrapper.get_stats = stats  # type: ignore[reportAttributeAccessIssue]
        wrapper.invalidate_containing = _invalidate_containing  # type: ignore[reportAttributeAccessIssue]
        return wrapper  # type: ignore[reportAttributeAccessIssue]

    return decorator
