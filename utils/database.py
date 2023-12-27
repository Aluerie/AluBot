from __future__ import annotations

import json
from typing import TYPE_CHECKING

import asyncpg

from config import POSTGRES_URL

if TYPE_CHECKING:
    pass


# TODO: PROPER ASYNCPG TYPING ACROSS THE WHOLE PROJECT
# hopefully somewhen asyncpg releases proper typing tools so
# * wait until then
# * rework all asyncpg typing so instead of our NamedTuple we can use something proper
# note that currently I'm using NamedTuple over DRecord bcs DRecord allows not-specified attributes too 
# so it's not precise typing wise

class DRecord(asyncpg.Record):
    """DRecord - Dot Record

        Same as `asyncpg.Record`, but allows dot-notations
        such as `record.id` instead of `record['id']`.

    Can also be used to type-hint the record.
    ```py
    class MyRecord(DRecord): #( asyncpg.Record):
        id: int
        name: str
        created_at: datetime.datetime

    r: MyRecord = ...
    reveal_type(r.id) # int
    ```
    """

    # Maybe typing situation will get better with
    # https://github.com/MagicStack/asyncpg/pull/577

    def __getattr__(self, name: str):
        return self[name]


async def create_pool() -> asyncpg.Pool:
    def _encode_jsonb(value):
        return json.dumps(value)

    def _decode_jsonb(value):
        return json.loads(value)

    async def init(con):
        await con.set_type_codec(
            "jsonb",
            schema="pg_catalog",
            encoder=_encode_jsonb,
            decoder=_decode_jsonb,
            format="text",
        )

    return await asyncpg.create_pool(
        POSTGRES_URL,
        init=init,
        command_timeout=60,
        min_size=20,
        max_size=20,
        record_class=DRecord,
        statement_cache_size=0,
    )  # type: ignore
