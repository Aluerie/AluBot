from __future__ import annotations

import asyncio
import enum
import logging
import random
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Coroutine, MutableMapping, Protocol, TypeVar

from aiohttp import ClientSession
from discord.utils import MISSING
from lru import LRU

from . import aluloop
from .bases import errors

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

if TYPE_CHECKING:
    from bot import AluBot

R = TypeVar("R")


class KeysCache:
    """KeysCache

    Caches the data from public json-urls
    for a certain amount of time just so we have somewhat up-to-date data
    and don't spam GET requests too often.

    The cache get updated by the aluloop task in the AluBot class.
    """

    def __init__(self, bot: AluBot) -> None:
        """_summary_

        Parameters
        ----------
        bot : AluBot
            We need it just so @aluloop task can find exc_manager in case of exceptions.
        """
        self.bot: AluBot = bot

        self.cached_data: dict[Any, Any] = {}
        self.lock: asyncio.Lock = asyncio.Lock()

        self.update_data.add_exception_type(errors.ResponseNotOK)
        self.update_data.change_interval(hours=24, minutes=random.randint(1, 59))
        self.update_data.start()

    async def get_response_json(self, url: str) -> Any:
        """Get response.json() from url with data"""
        async with self.bot.session.get(url=url) as response:
            if response.ok:
                # https://stackoverflow.com/a/48842348/19217368
                # `content = None` disables the check and kinda sets it to `content_type=response.content_type`
                return await response.json(content_type=None)

        # response not ok
        # so we raise an error that is `add_exception_type`'ed so the task can run exp backoff
        status = response.status
        response_text = await response.text()
        log.debug("Key Cache response error: %s %s", status, response_text)
        raise errors.ResponseNotOK(f"Key Cache response error: {status} {response_text}")

    async def fill_data(self) -> dict[Any, Any]:
        """Fill self.cached_data with the data from various json data

        This function is supposed to be implemented by subclasses.
        We get the data and sort it out into a convenient dictionary to cache.
        """
        ...

    @aluloop()
    async def update_data(self):
        """The task responsible for keeping the data up-to-date."""
        async with self.lock:
            self.cached_data = await self.fill_data()

    # methods to actually get the data from cache

    async def get_cached_data(self) -> dict[Any, Any]:
        """Get the whole cached data"""
        if self.cached_data:
            return self.cached_data
        else:
            await self.update_data()
            return self.cached_data

    async def get_value(self, cache: str, key: Any) -> Any:
        """Get value by the `key` from the sub-cache named `cache` in the `self.cached_data`."""
        try:
            return self.cached_data[cache][key]
        except KeyError:
            # let's try to update the cache in case it's a KeyError due to
            # * new patch or something
            # * the data is not initialized then we will get stuck in self.lock waiting for the data.
            await self.update_data()
            return self.cached_data[cache][key]

    async def get_cache(self, cache: str) -> dict[Any, Any]:
        """Get the whole sub-cache dict."""
        try:
            return self.cached_data[cache]
        except KeyError:
            await self.update_data()
            return self.cached_data[cache]


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


class ExpiringCache(dict):
    def __init__(self, seconds: float):
        self.__ttl: float = seconds
        super().__init__()

    def __verify_cache_integrity(self):
        # Have to do this in two steps...
        current_time = time.monotonic()
        to_remove = [k for (k, (v, t)) in super().items() if current_time > (t + self.__ttl)]
        for k in to_remove:
            del self[k]

    def get(self, key: str, default: Any = None):
        v = super().get(key, default)
        if v is default:
            return default
        return v[0]

    def __contains__(self, key: str):
        self.__verify_cache_integrity()
        return super().__contains__(key)

    def __getitem__(self, key: str):
        self.__verify_cache_integrity()
        v, _ = super().__getitem__(key)
        return v

    def __setitem__(self, key: str, value: Any):
        super().__setitem__(key, (value, time.monotonic()))

    def values(self):
        return map(lambda x: x[0], super().values())

    def items(self):
        return map(lambda x: (x[0], x[1][0]), super().items())


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
            def _true_repr(o):
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
        def wrapper(*args: Any, **kwargs: Any):
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
            to_remove = []
            for k in _internal_cache.keys():
                if key in k:
                    to_remove.append(k)
            for k in to_remove:
                try:
                    del _internal_cache[k]
                except KeyError:
                    continue

        # TODO: investigate those # type: ignore
        wrapper.cache = _internal_cache  # type: ignore
        wrapper.get_key = lambda *args, **kwargs: _make_key(args, kwargs)  # type: ignore
        wrapper.invalidate = _invalidate  # type: ignore
        wrapper.get_stats = _stats  # type: ignore
        wrapper.invalidate_containing = _invalidate_containing  # type: ignore
        return wrapper  # type: ignore

    return decorator
