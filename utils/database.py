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
        min_size=10,
        max_size=10,
        record_class=DRecord,
        statement_cache_size=0,
    ) # type: ignore


# SQL RECIPES BCS I ALWAYS FORGET
""" 
--- recipe for converting column to tz aware 
ALTER TABLE botinfo ALTER COLUMN git_checked_dt
TYPE TIMESTAMPTZ USING git_checked_dt AT TIME ZONE 'UTC' ;

-- recipe to set default 
ALTER TABLE users ALTER COLUMN created_at
SET DEFAULT (now() at time zone 'utc');

-- recipe to INSERT and return True/None if it was success
INSERT INTO users (id, name) 
VALUES ($1, $2) 
ON CONFLICT DO NOTHING
RETURNING True;
-- ### value = await self.bot.pool.fetchval(query, 333356, 'hi')

--- recipe to add a new column
ALTER TABLE dota_matches
ADD COLUMN live BOOLEAN DEFAULT TRUE;

--- recipe to get all column names
SELECT column_name
FROM information_schema.columns
WHERE table_name=$1;

---------
WITH foo AS (SELECT array(SELECT dotafeed_stream_ids
FROM guilds
WHERE id = 759916212842659850))
SELECT display_name
FROM dota_players p
WHERE NOT p.id=ANY(foo)
ORDER BY similarity(display_name, 'gorgc') DESC
LIMIT 12;
"""
