from __future__ import annotations

import asyncio
import enum
import logging
import random
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, override

import orjson

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


class KeysCache:
    """KeysCache.

    Caches the data from public json-urls
    for a certain amount of time just so we have somewhat up-to-date data
    and don't spam GET requests too often.

    The cache get updated by the aluloop task in the AluBot class.

    Subclasses must implement
    ```py
        async def fill_data(self) -> CacheDict:
    ```
    and return Cache dictionary that is going to be put into self.cached_data.

    The structure of `self.cached_data` can be anything but for the purposes of
    dota_cache, cdragon cache it should be a dict so the key `champion_id` in the following example:
    >>> champion = 910
    >>> cdragon.champion.cached_data['name_by_id'][champion_id]
    >>> "Hwei"
    can be reached for the purposes of `get_value` function.

    This is kinda implementation on "it just works" basis but oh well,
    I'm not developing a library here, am I?
    """

    # TODO: refactor this cache thing so it's more clear what is what
    # i.e. cache = whole class
    # cached_data -> rename to data
    # think of a name for data category maybe like mapping name
    # and think of a name for value keys thing idk
    if TYPE_CHECKING:
        cached_data: CacheDict

    def __init__(self, bot: AluBot) -> None:
        """__init__.

        Parameters
        ----------
        bot : AluBot
            We need it just so @aluloop task can find exc_manager in case of exceptions.

        """
        self.bot: AluBot = bot

        self.lock: asyncio.Lock = asyncio.Lock()

        self.update_data.add_exception_type(errors.ResponseNotOK)
        # random times just so we don't have a possibility of all cache being updated at the same time
        self.update_data.change_interval(hours=24, minutes=random.randint(1, 59))
        self.update_data.start()

    async def get_response_json(self, url: str) -> Any:
        """Get response.json() from url with data."""
        async with self.bot.session.get(url=url) as response:
            if response.ok:
                # https://stackoverflow.com/a/48842348/19217368
                # `content = None` disables the check and kinda sets it to `content_type=response.content_type`
                return await response.json(content_type=None, loads=orjson.loads)

        # response not ok
        # so we raise an error that is `add_exception_type`'ed so the task can run exp backoff
        status = response.status
        response_text = await response.text()
        log.debug("Key Cache response error: %s %s", status, response_text)
        msg = f"Key Cache response error: {status} {response_text}"
        raise errors.ResponseNotOK(msg)

    async def fill_data(self) -> CacheDict:
        """Fill self.cached_data with the data from various json data.

        This function is supposed to be implemented by subclasses.
        We get the data and sort it out into a convenient dictionary to cache.
        """
        ...

    @aluloop()
    async def update_data(self) -> None:
        """The task responsible for keeping the data up-to-date."""
        # log.debug("Trying to update Cache %s.", self.__class__.__name__)
        async with self.lock:
            start_time = time.perf_counter()
            self.cached_data = await self.fill_data()
            log.debug("Cache %s is updated in %.5f", self.__class__.__name__, time.perf_counter() - start_time)

    # methods to actually get the data from cache

    async def get_cached_data(self) -> CacheDict:
        """Get the whole cached data."""
        try:
            return self.cached_data
        except AttributeError:
            await self.update_data()
            return self.cached_data

    async def get_value(self, cache: str, key: Any) -> Any:
        """Get value by the `key` from the sub-cache named `cache` in the `self.cached_data`."""
        try:
            return self.cached_data[cache][key]
        except (KeyError, AttributeError):
            # let's try to update the cache in case it's a KeyError due to
            # * new patch or something
            # * the data is not initialized then we will get stuck in self.lock waiting for the data.
            await self.update_data()
            return self.cached_data[cache][key]

    async def get_value_or_none(self, cache: str, key: Any) -> Any:
        """Same as get but sometimes we don't want to refresh the data on KeyError since we expect to hit it.

        For example, when we try to find Dota talent name, we query ability ids into it that aren't talents.
        """
        data = await self.get_cached_data()
        return data[cache].get(key)

    async def get_cache(self, cache: str) -> dict[Any, Any]:
        """Get the whole sub-cache dict."""
        try:
            return self.cached_data[cache]
        except (KeyError, AttributeError):
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
