"""Database `asyncpg.Record` type solution.

Unfortunately, `asyncpg` typing is a nightmare. Even though, pip install asyncpg-stubs`
(https://github.com/MagicStack/asyncpg/pull/577) helps

But we still want some way to type-hint query results. This is how we currently do it:

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
This "kinda" works because we declared `fetch`, `fetchrow` return type as `Any` despite
`asyncpg-stubs` declaring it as `asyncpg.Record`. Just remember the differences
between `TypedDict` and `Record` and manually resort them, if we ever actually face any problems with it.

PS for more understanding:
* `asyncpg.Record` is a cut-off version of both `dict` and `tuple` classes:
    click `asyncpg.Record` declaration for its supported methods.
    This is why if Python ever introduces possibility to extend the capability of typed dict
    (e.g. We can bind it to something else's getitem etc) we can't really type-hint Record properly.
"""

from typing import Any, override

import asyncpg


class PoolTypedWithAny(asyncpg.Pool[asyncpg.Record]):
    """Fake Type Class.

    For typing purposes, our `bot.pool` will be "type-ignore"'d-as `PoolTypedWithAny`
    that allows us to properly type the return values via narrowing like mentioned in instructions above
    without hundreds of "type: ignore" notices for each TypedDict.

    * Right now, `asyncpg` is untyped so this is better than the current status quo
    """

    # all methods below were changed from "asyncpg.Record" to "Any"

    @override
    async def fetch(self, query: str, *args: Any, timeout: float | None = None) -> list[Any]: ...

    @override
    async def fetchrow(self, query: str, *args: Any, timeout: float | None = None) -> Any: ...
