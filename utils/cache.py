from __future__ import annotations

import abc
import asyncio
import enum
import logging
import random
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar, override

# from aiohttp import ClientSession
# from discord.utils import MISSING
from lru import LRU

from bot import aluloop

from . import errors

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator, MutableMapping

    from bot import AluBot

R = TypeVar("R")

type CacheDict = dict[Any, Any]
CachedDataT = TypeVar("CachedDataT", bound=CacheDict)

VT = TypeVar("VT")


class NewKeysCache(Generic[VT]):
    if TYPE_CHECKING:
        cached_data: dict[int, VT]

    def __init__(self, bot: AluBot) -> None:
        """_summary_

        Parameters
        ----------
        bot
            need it just so @aluloop task can use `exc_manager` to send an error notification.
        """
        self.bot: AluBot = bot
        self.lock: asyncio.Lock = asyncio.Lock()

    def start(self) -> None:
        # self.update_data.add_exception_type(errors.ResponseNotOK)
        # random times just so we don't have a possibility of all cache being updated at the same time
        self.update_data.change_interval(hours=24, minutes=random.randint(1, 59))
        self.update_data.start()

    def close(self) -> None:
        """Closes the keys cache."""
        self.update_data.cancel()

    async def fill_data(self) -> dict[int, VT]:
        ...

    @aluloop()
    async def update_data(self) -> None:
        async with self.lock:
            start_time = time.perf_counter()
            self.cached_data = await self.fill_data()
            log.info("Cache %s is updated in %.5f", self.__class__.__name__, time.perf_counter() - start_time)

    async def get_cached_data(self) -> dict[int, VT]:
        """Get the whole cached data."""
        try:
            return self.cached_data
        except AttributeError:
            await self.update_data()
            return self.cached_data

    async def get_value(self, id: int) -> VT:
        try:
            return self.cached_data[id]
        except (KeyError, AttributeError):
            await self.update_data()
            return self.cached_data[id]


class CharacterCache(abc.ABC):
    @abc.abstractmethod
    async def id_by_display_name(self, character_name: str) -> int:
        ...

    @abc.abstractmethod
    async def display_name_by_id(self, character_id: int) -> str:
        ...

    @abc.abstractmethod
    async def id_display_name_tuples(self) -> list[tuple[int, str]]:
        ...

    @abc.abstractmethod
    async def id_display_name_dict(self) -> dict[int, str]:
        ...


# Can't use ParamSpec due to https://github.com/python/typing/discussions/946
class CacheProtocol(Protocol[R]):
    cache: MutableMapping[str, asyncio.Task[R]]

    def __call__(self, *args: Any, **kwds: Any) -> asyncio.Task[R]:
        ...

    def get_key(self, *args: Any, **kwargs: Any) -> str:
        ...

    def invalidate(self, *args: Any, **kwargs: Any) -> bool:
        ...

    def invalidate_containing(self, key: str) -> None:
        ...

    def get_stats(self) -> tuple[int, int]:
        ...


class ExpiringCache(dict[Any, Any]):
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
    ignore_kwargs: bool = False,
) -> Callable[[Callable[..., Coroutine[Any, Any, R]]], CacheProtocol[R]]:
    def decorator(func: Callable[..., Coroutine[Any, Any, R]]) -> CacheProtocol[R]:
        if strategy is Strategy.lru:
            _internal_cache = LRU(maxsize)
            _stats = _internal_cache.get_stats
        elif strategy is Strategy.raw:
            _internal_cache = {}
            _stats = lambda: (0, 0)
        elif strategy is Strategy.timed:
            _internal_cache = ExpiringCache(seconds=maxsize)
            _stats = lambda: (0, 0)

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
                    if k == "connection" or k == "pool":
                        continue

                    key.append(_true_repr(k))
                    key.append(_true_repr(v))

            return ":".join(key)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> asyncio.Task[Any]:  # is it proper type?
            key = _make_key(args, kwargs)
            try:
                task = _internal_cache[key]
            except KeyError:
                _internal_cache[key] = task = asyncio.create_task(func(*args, **kwargs))
                return task
            else:
                return task

        def _invalidate(*args: Any, **kwargs: Any) -> bool:
            try:
                del _internal_cache[_make_key(args, kwargs)]
            except KeyError:
                return False
            else:
                return True

        def _invalidate_containing(key: str) -> None:
            to_remove = [k for k in _internal_cache if key in k]
            for k in to_remove:
                try:
                    del _internal_cache[k]
                except KeyError:
                    continue

        # TODO: investigate those "type: ignore"
        wrapper.cache = _internal_cache  # type: ignore
        wrapper.get_key = lambda *args, **kwargs: _make_key(args, kwargs)  # type: ignore
        wrapper.invalidate = _invalidate  # type: ignore
        wrapper.get_stats = _stats  # type: ignore
        wrapper.invalidate_containing = _invalidate_containing  # type: ignore
        return wrapper  # type: ignore

    return decorator
