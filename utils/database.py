"""Database Utilities.

Unfortunately, `asyncpg` typing is a nightmare. https://github.com/MagicStack/asyncpg/pull/577
So here are some instructions that we follow across the project.

* installed stubs from `pip install asyncpg-stubs` solve a problem of untyped pool's methods.

However, we still want to type-hint query results.
The current way for it is to combine a `TypedDict` with "# type: ignore" like

```py
class UserRow(TypedDict):
    id: int
    name: str

async def beta_task(self) -> None:
    query = "SELECT id, name FROM users WHERE id=$1"
    row: UserRow = await self.bot.pool.fetchrow(query, const.User.aluerie)  # type: ignore # asyncpg
    if row:
        reveal_type(row)  # UserRow
        reveal_type((row["id"]))  # int
        reveal_type(row.get("xd", None))  # Any | None
        reveal_type(row.id)  # Cannot access member "id" for type "UserRow"
```
"""

from __future__ import annotations

from typing import Any

import asyncpg
import orjson

from config import POSTGRES_URL


async def create_pool() -> asyncpg.Pool[asyncpg.Record]:
    def _encode_jsonb(value: Any) -> str:
        return orjson.dumps(value).decode("utf-8")

    def _decode_jsonb(value: str) -> Any:
        return orjson.loads(value)

    async def init(con: asyncpg.Connection[asyncpg.Record]) -> None:
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
        record_class=DotRecord,
        statement_cache_size=0,
    )  # type: ignore # why does it think it can return None?


class DotRecord(asyncpg.Record):
    """Dot Record

    Same as `asyncpg.Record`, but allows dot-notations
    such as `record.id` instead of `record['id']`.
    """

    def __getattr__(self, name: str) -> Any:
        return self[name]
