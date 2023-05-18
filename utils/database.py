from __future__ import annotations
from typing import TYPE_CHECKING

import json

import asyncpg

from config import POSTGRES_URL


if TYPE_CHECKING:
    pass


class DRecord(asyncpg.Record):
    """DRecord - Dot Record

    Same as `asyncpg.Record`, but allows dot-notations
    such as `record.id` instead of `record['id']`.
    """

    def __getattr__(self, name: str):
        return self[name]


async def create_pool() -> asyncpg.Pool:
    def _encode_jsonb(value):
        return json.dumps(value)

    def _decode_jsonb(value):
        return json.loads(value)

    async def init(con):
        await con.set_type_codec(
            'jsonb',
            schema='pg_catalog',
            encoder=_encode_jsonb,
            decoder=_decode_jsonb,
            format='text',
        )

    return await asyncpg.create_pool(
        POSTGRES_URL,
        init=init,
        command_timeout=60,
        min_size=20,
        max_size=20,
        record_class=DRecord,
        statement_cache_size=0,
    ) # type: ignore



