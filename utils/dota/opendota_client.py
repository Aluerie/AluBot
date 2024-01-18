from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
            json_response_middleware(),
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

    async def test_opendota_client():
        async with OpenDotaClient() as opendota_client:
            match = await opendota_client.get_match(match_id=7540506660)
            for word in ["players", "picks_bans", "draft_timings", "cosmetics", "objectives"]:
                match.pop(word)  # type: ignore
            print(match["od_data"]["has_parsed"])
            pprint.pprint(match)
            # pprint.pprint(match["players"][2])

    asyncio.run(test_opendota_client())
