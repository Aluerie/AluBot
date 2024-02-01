"""Database Utilities.

# Section #0. Typing Problem

Unfortunately, `asyncpg` typing is a nightmare.
* https://github.com/MagicStack/asyncpg/pull/577
* installed stubs from `pip install asyncpg-stubs`.

But we still want some way to type-hint query results. And this is how we do it:

```py
class UserRow(TypedDict):
    id: int
    name: str

async def beta_task(self) -> None:
    query = "SELECT id, name FROM users WHERE id=$1"
    row: UserRow = await self.bot.pool.fetchrow(query, const.User.aluerie)
    if row:
        reveal_type(row)  # UserRow
        reveal_type((row["id"]))  # int
        reveal_type(row.get("xd", None))  # Any | None
        reveal_type(row.id)  # Cannot access member "id" for type "UserRow"
```
This kinda works because we declared `fetch`, `fetchrow` return type as `Any` despite
`asyncpg-stubs` declaring it as `asyncpg.Record`.

Just remember the differences between TypedDict and Record and manually resort them,
if we ever actually face any problems with it.

PS for more understanding:
* asyncpg.Record is a cut-off version of both dict and tuple classes:
    click "DotRecord(asyncpg.Record)" declaration for its supported methods.
    This is why if Python ever introduces possibility to extend the capability of typed dict
    (e.g. We can bind it to something else's getitem etc) we can't really type-hint Record properly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Self

import asyncpg
import orjson

from config import POSTGRES_URL

if TYPE_CHECKING:
    from types import TracebackType

    from asyncpg import Connection

    xd = asyncpg.Pool


class DotRecord(asyncpg.Record):
    """Dot Record.

    Same as `asyncpg.Record`, but allows dot-notations
    such as `record.id` instead of `record['id']`.
    """

    def __getattr__(self, name: str) -> Any:
        return self[name]


class PoolAcquireContext(Protocol):
    async def __aenter__(self) -> Connection[DotRecord]:
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        ...


# For typing purposes, our `bot.pool` will be PoolProtocol
# that allows us to properly type the return values
# via narrowing like mentioned in instructions above
# without hundreds of "type: ignore" notices for each TypedDict.

# Right now, asyncpg is untyped so this is better than the current status quo
# If we ever need the regular Pool type we have `bot.database` without any Protocol shenanigans,
# * to check default type-hinting
# * to quickly check official docs for Pool methods since (protocol ones are empty and `copy_doc` won't work for vscode)
# it returns types from `asyncpg-stubs`


class PoolProtocol(Protocol):
    def acquire(self, *, timeout: float | None = None) -> PoolAcquireContext:
        ...

    async def execute(self, query: str, *args: Any, timeout: float | None = None) -> str:
        ...

    async def executemany(self, query: str, *args: Any, timeout: float | None = None) -> None:
        ...

    async def fetch(self, query: str, *args: Any, timeout: float | None = None) -> list[Any]:
        ...

    async def fetchrow(self, query: str, *args: Any, timeout: float | None = None) -> Any | None:
        ...

    def release(self, connection: Connection[DotRecord]) -> None:
        ...

    async def __aenter__(self) -> Self:
        ...

    async def __aexit__(self, *exc: Any) -> None:  # exc_type, exc_value, exc_tb
        ...


async def create_pool() -> asyncpg.Pool[DotRecord]:
    def _encode_jsonb(value: Any) -> str:
        return orjson.dumps(value).decode("utf-8")

    def _decode_jsonb(value: str) -> Any:
        return orjson.loads(value)

    async def init(con: asyncpg.Connection[DotRecord]) -> None:
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
        record_class=DotRecord,  # todo: change this to asyncpg.Record once we remove all dotted notations.
        statement_cache_size=0,
    )  # type: ignore # why does it think it can return None?
