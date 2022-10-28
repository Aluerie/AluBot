"""
The MIT License (MIT)

"""
import asyncio
from datetime import datetime, timedelta, timezone

from aiohttp import ClientSession
from pyot.utils.functools import async_property


async def get_resp_json(*, url: str) -> dict:
    async with ClientSession() as session:
        resp = await session.request("GET", url)
        if not (resp and resp.status == 200):
            raise RuntimeError(f'Dota constants failed with status {resp.status}')
            # return self.cached_data
        return await resp.json()  # abilities


class KeyCache:

    def __init__(self) -> None:
        self.cached_data = {}
        self.lock = asyncio.Lock()
        self.last_updated = datetime.now(timezone.utc) - timedelta(days=1)

    async def get_resp_json(self, url: str):
        try:
            return await get_resp_json(url=url)
        except RuntimeError as exc:
            if any(self.cached_data.values()):
                return self.cached_data
            else:
                raise exc

    async def fill_data(self) -> dict:
        ...

    @async_property
    async def data(self):
        if datetime.now(timezone.utc) - self.last_updated < timedelta(hours=3):
            return self.cached_data
        async with self.lock:
            if datetime.now(timezone.utc) - self.last_updated < timedelta(hours=3):
                return self.cached_data

            self.cached_data = await self.fill_data()
            self.last_updated = datetime.now(timezone.utc)
        return self.cached_data
