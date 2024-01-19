from __future__ import annotations

from typing import TYPE_CHECKING, Any

import orjson
from pulsefire.clients import BaseClient
from pulsefire.middlewares import http_error_middleware, json_response_middleware

if TYPE_CHECKING:
    from pulsefire.clients import Middleware

    from .opendota_schemas import OpenDotaAPISchema

__all__ = ("OpenDotaClient",)


class OpenDotaClient(BaseClient):
    def __init__(
        self,
        *,
        base_url: str = "https://api.opendota.com/api",
        default_params: dict[str, Any] = {},
        default_headers: dict[str, str] = {},
        default_queries: dict[str, str] = {},
        middlewares: list[Middleware] = [
            json_response_middleware(orjson.loads),
            http_error_middleware(),
        ],
    ) -> None:
        super().__init__(
            base_url=base_url,
            default_params=default_params,
            default_headers=default_headers,
            default_queries=default_queries,
            middlewares=middlewares,
        )

    async def get_match(self, *, match_id: int) -> OpenDotaAPISchema.Match:
        return await self.invoke("GET", f"/matches/{match_id}")  # type: ignore

    async def request_parse(self, *, match_id: int) -> OpenDotaAPISchema.ParseJob:
        return await self.invoke("POST", f"/request/{match_id}")  # type: ignore


if __name__ == "__main__":
    import asyncio
    import pprint

    async def test_opendota_get_match():
        async with OpenDotaClient() as opendota_client:
            match = await opendota_client.get_match(match_id=7544944551)
            player = match["players"][5]
            pprint.pprint(list(player.keys()))
            pprint.pprint(player["account_id"])
            # match.pop('players') # type: ignore
            # pprint.pprint(match.keys())
            # pprint.pprint(match["players"][2])

    async def test_opendota_request_parse():
        async with OpenDotaClient() as opendota_client:
            job = await opendota_client.request_parse(match_id=7543594334)
            pprint.pprint(job)

    asyncio.run(test_opendota_get_match())
