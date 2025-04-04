from __future__ import annotations

import collections
import random
import time
from typing import TYPE_CHECKING, Any, override

import aiohttp
import orjson
from pulsefire.clients import BaseClient
from pulsefire.middlewares import http_error_middleware, json_response_middleware, rate_limiter_middleware
from pulsefire.ratelimiters import BaseRateLimiter

try:
    from config import config

    from ....utils import errors
except ImportError:
    import sys

    sys.path.append("D:/LAPTOP/AluBot")
    from config import config
    from utils import errors

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pulsefire.invocation import Invocation

    from .schemas import odota_constants, opendota, steam_web_api, stratz

__all__ = (
    "OpenDotaClient",
    "OpenDotaConstantsClient",
    "SteamWebAPIClient",
    "StratzClient",
)

type HeaderRateLimitInfo = Mapping[str, Sequence[tuple[int, int]]]


class DotaAPIsRateLimiter(BaseRateLimiter):
    """Dota 2 APIs rate limiter.

    This rate limiter can be served stand-alone for centralized rate limiting.
    """

    def __init__(self) -> None:
        self._track_syncs: dict[str, tuple[float, list[Any]]] = {}
        self.rate_limits_string: str = "Not Set Yet"
        self.rate_limits_ratio: float = 1.0
        self._index: dict[tuple[str, int, Any, Any, Any], tuple[int, int, float, float, float]] = (
            collections.defaultdict(lambda: (0, 0, 0, 0, 0))
        )

    @override
    async def acquire(self, invocation: Invocation) -> float:
        wait_for = 0
        pinging_targets = []
        requesting_targets = []
        request_time = time.time()
        for target in [
            ("app", 0, invocation.params.get("region", ""), invocation.method, invocation.urlformat),
            ("app", 1, invocation.params.get("region", ""), invocation.method, invocation.urlformat),
        ]:
            count, limit, expire, latency, pinged = self._index[target]
            pinging = pinged and request_time - pinged < 10
            if pinging:
                wait_for = max(wait_for, 0.1)
            elif request_time > expire:
                pinging_targets.append(target)
            elif request_time > expire - latency * 1.1 + 0.01 or count >= limit:
                wait_for = max(wait_for, expire - request_time)
            else:
                requesting_targets.append(target)
        if wait_for <= 0:
            if pinging_targets:
                self._track_syncs[invocation.uid] = (request_time, pinging_targets)
                for pinging_target in pinging_targets:
                    self._index[pinging_target] = (0, 0, 0, 0, time.time())
                wait_for = -1
            for requesting_target in requesting_targets:
                count, *values = self._index[requesting_target]
                self._index[requesting_target] = (count + 1, *values)  # type: ignore[reportArgumentType]

        return wait_for

    @override
    async def synchronize(self, invocation: Invocation, headers: dict[str, str]) -> None:
        response_time = time.time()
        request_time, pinging_targets = self._track_syncs.pop(invocation.uid, [None, None])
        if request_time is None:
            return

        if random.random() < 0.1:
            for prev_uid, (prev_request_time, _) in self._track_syncs.items():
                if response_time - prev_request_time > 600:
                    self._track_syncs.pop(prev_uid, None)

        try:
            header_limits, header_counts = self.analyze_headers(headers)
        except KeyError:
            for pinging_target in pinging_targets:  # type: ignore[reportArgumentType]
                self._index[pinging_target] = (0, 0, 0, 0, 0)
            return
        for scope, idx, *subscopes in pinging_targets:  # type: ignore[reportArgumentType]
            if idx >= len(header_limits[scope]):
                self._index[scope, idx, *subscopes] = (0, 10**10, response_time + 3600, 0, 0)
                continue
            self._index[scope, idx, *subscopes] = (
                header_counts[scope][idx][0],
                header_limits[scope][idx][0],
                header_limits[scope][idx][1] + response_time,
                response_time - request_time,
                0,
            )

    def analyze_headers(self, headers: dict[str, str]) -> tuple[HeaderRateLimitInfo, HeaderRateLimitInfo]:
        raise NotImplementedError


class OpenDotaAPIRateLimiter(DotaAPIsRateLimiter):
    @override
    def analyze_headers(self, headers: dict[str, str]) -> tuple[HeaderRateLimitInfo, HeaderRateLimitInfo]:
        self.rate_limits_string = "\n".join(
            [f"{timeframe}: {headers[f'X-Rate-Limit-Remaining-{timeframe}']}" for timeframe in ("Minute", "Day")],
        )
        self.rate_limits_ratio = int(headers["X-Rate-Limit-Remaining-Day"]) / 2000

        header_limits = {
            "app": [(60, 60), (2000, 60 * 60 * 24)],
        }
        header_counts = {
            "app": [
                (int(headers[f"X-Rate-Limit-Remaining-{name}"]), period)
                for name, period in [("Minute", 60), ("Day", 60 * 60 * 24)]
            ],
        }
        return header_limits, header_counts


class OpenDotaClient(BaseClient):
    """Pulsefire client for OpenDota API."""

    def __init__(self) -> None:
        self.rate_limiter = OpenDotaAPIRateLimiter()
        super().__init__(
            base_url="https://api.opendota.com/api",
            default_params={},
            default_headers={},
            default_queries={},
            middlewares=[
                json_response_middleware(orjson.loads),
                http_error_middleware(),
                rate_limiter_middleware(self.rate_limiter),
            ],
        )

    async def get_match(self, *, match_id: int) -> opendota.MatchResponse:
        """GET matches/{match_id}."""
        return await self.invoke("GET", f"/matches/{match_id}")  # type: ignore[reportReturnType]

    async def request_parse(self, *, match_id: int) -> opendota.ParseResponse:
        """POST /request/{match_id}."""
        return await self.invoke("POST", f"/request/{match_id}")  # type: ignore[reportReturnType]


class OpenDotaConstantsClient(BaseClient):
    """Pulsefire client to work with OpenDota constants.

    This client works with odota/dotaconstants repository.
    https://github.com/odota/dotaconstants
    """

    def __init__(self) -> None:
        super().__init__(
            # could use `https://api.opendota.com/api/constants` but sometimes they update the repo first
            # and forget to update the site backend x_x
            base_url="https://raw.githubusercontent.com/odota/dotaconstants/master/build",
            default_params={},
            default_headers={},
            default_queries={},
            middlewares=[
                json_response_middleware(orjson.loads),
                http_error_middleware(),
            ],
        )

    async def get_heroes(self) -> odota_constants.GetHeroesResponse:
        """Get `heroes.json` data.

        https://raw.githubusercontent.com/odota/dotaconstants/master/build/heroes.json
        """
        return await self.invoke("GET", "/heroes.json")  # type: ignore[reportReturnType]

    async def get_ability_ids(self) -> odota_constants.GetAbilityIDsResponse:
        """Get `ability_ids.json` data.

        https://raw.githubusercontent.com/odota/dotaconstants/master/build/ability_ids.json
        """
        return await self.invoke("GET", "/ability_ids.json")  # type: ignore[reportReturnType]

    async def get_abilities(self) -> odota_constants.GetAbilitiesResponse:
        """Get `abilities.json` data.

        https://raw.githubusercontent.com/odota/dotaconstants/master/build/abilities.json
        """
        return await self.invoke("GET", "/abilities.json")  # type: ignore[reportReturnType]

    async def get_hero_abilities(self) -> odota_constants.GetHeroAbilitiesResponse:
        """Get `hero_abilities.json` data.

        https://raw.githubusercontent.com/odota/dotaconstants/master/build/hero_abilities.json.
        """
        return await self.invoke("GET", "/hero_abilities.json")  # type: ignore[reportReturnType]

    async def get_items(self) -> odota_constants.GetItemsResponse:
        """Get `items.json` data.

        https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json
        """
        return await self.invoke("GET", "/items.json")  # type: ignore[reportReturnType]


class SteamWebAPIClient(BaseClient):
    """Pulsefire client to work with Steam Web API."""

    def __init__(self) -> None:
        super().__init__(
            base_url="https://api.steampowered.com/",
            default_params={},
            default_headers={},
            default_queries={"key": config["TOKENS"]["STEAM"]},
            middlewares=[
                json_response_middleware(orjson.loads),
                http_error_middleware(),
            ],
        )

    async def get_match_details(self, match_id: int) -> steam_web_api.MatchDetailsResponse:
        """GET /IDOTA2Match_570/GetMatchDetails/v1/.

        https://steamapi.xpaw.me/#IDOTA2Match_570/GetMatchDetails.
        """
        queries = {"match_id": match_id}  # noqa: F841
        return await self.invoke("GET", "/IDOTA2Match_570/GetMatchDetails/v1/")  # type: ignore[reportReturnType]

    async def get_real_time_stats(self, server_steam_id: int) -> steam_web_api.RealTimeStatsResponse:
        """GET /IDOTA2Match_570/GetMatchDetails/v1/.

        https://steamapi.xpaw.me/#IDOTA2MatchStats_570/GetRealtimeStats.
        """
        queries = {"server_steam_id": server_steam_id}  # noqa: F841
        return await self.invoke("GET", "/IDOTA2MatchStats_570/GetRealtimeStats/v1/")  # type: ignore[reportReturnType]


class StratzAPIRateLimiter(DotaAPIsRateLimiter):
    @override
    def analyze_headers(self, headers: dict[str, str]) -> tuple[HeaderRateLimitInfo, HeaderRateLimitInfo]:
        self.rate_limits_string = "\n".join(
            [
                f"{timeframe}: "
                f"{headers[f'X-RateLimit-Remaining-{timeframe}']}/{headers[f'X-RateLimit-Limit-{timeframe}']}"
                for timeframe in ("Second", "Minute", "Hour", "Day")
            ],
        )
        self.rate_limits_ratio = int(headers["X-RateLimit-Remaining-Day"]) / int(headers["X-RateLimit-Limit-Day"])

        periods = [
            ("Second", 1),
            ("Minute", 60),
            ("Hour", 60 * 60),
            ("Day", 60 * 60 * 24),
        ]
        header_limits = {"app": [(int(headers[f"X-RateLimit-Limit-{name}"]), period) for name, period in periods]}
        header_counts = {"app": [(int(headers[f"X-RateLimit-Remaining-{name}"]), period) for name, period in periods]}
        return header_limits, header_counts


class StratzClient(BaseClient):
    """Pulsefire client to boilerplate work with Stratz GraphQL queries.

    You can play around with queries here: https://api.stratz.com/graphiql/
    Note "i" means it's a fancy UI version.
    """

    def __init__(self) -> None:
        self.rate_limiter = StratzAPIRateLimiter()
        super().__init__(
            base_url="https://api.stratz.com/graphql",
            default_params={},
            default_headers={
                "User-Agent": "STRATZ_API",
                "Authorization": f"Bearer {config['TOKENS']['STRATZ_BEARER']}",
                "Content-Type": "application/json",
            },
            default_queries={},
            middlewares=[
                json_response_middleware(orjson.loads),
                http_error_middleware(),
                rate_limiter_middleware(self.rate_limiter),
            ],
        )

    async def invoke_with_try(self, query: str, json: dict[str, Any]) -> Any:
        """Error wrapper for `self.invoker`.

        Notes
        -----
        * The reason for this function is that sometimes I forget Stratz resets Bearer Tokens every ~365 days
            or when they suspect something. In these cases, the bot starts erroring out with 403
            while I start to panic (when I did nothing wrong).
            Unfortunately, they don't notify people about token resets.
        """
        try:
            return await self.invoke("POST", "")
        except aiohttp.ClientResponseError as exc:
            if exc.status == 403:
                msg = (
                    "403 Forbidden. Please, check if your Bearer Token in config.py matches "
                    "the one at https://stratz.com/api. "
                    "PS. This error is manual and not given by Stratz API."
                )
                raise errors.ResponseNotOK(msg) from None
            raise

    async def get_fpc_match_to_edit(self, *, match_id: int, friend_id: int) -> stratz.FPCMatchesResponse:
        """Queries info that I need to know in order to edit Dota 2 FPC notification."""
        query = """
query GetFPCMatchToEdit ($match_id: Long!, $friend_id: Long!) {
    match(id: $match_id) {
        statsDateTime
        players(steamAccountId: $friend_id) {
            isVictory
            heroId
            variant
            kills
            deaths
            assists
            item0Id
            item1Id
            item2Id
            item3Id
            item4Id
            item5Id
            neutral0Id
            playbackData {
                abilityLearnEvents {
                    abilityId
                }
                purchaseEvents {
                    time
                    itemId
                }
            }
            stats {
                matchPlayerBuffEvent {
                    itemId
                }
            }
        }
    }
}"""
        json = {"query": query, "variables": {"match_id": match_id, "friend_id": friend_id}}
        return await self.invoke_with_try(query, json)

    async def get_heroes(self) -> stratz.HeroesResponse:
        """Queries Dota 2 Hero Constants."""
        query = """
query Heroes {
    constants {
        heroes {
            id
            shortName
            displayName
            abilities {
                ability {
                    id
                    name
                }
            }
            talents {
                abilityId
            }
            facets {
                facetId
            }
        }
    }
}
        """
        json = {"query": query}
        return await self.invoke_with_try(query, json)

    async def get_abilities(self) -> stratz.AbilitiesResponse:
        """Queries Dota 2 Hero Ability Constants."""
        query = """
query Abilities {
    constants {
        abilities {
            id
            name
            language {
                displayName
            }
            isTalent
        }
    }
}"""
        json = {"query": query}
        return await self.invoke_with_try(query, json)

    async def get_items(self) -> stratz.ItemsResponse:
        """Queries Dota 2 Hero Item Constants."""
        query = """
query Items {
    constants {
        items {
            id
            shortName
        }
    }
}"""
        json = {"query": query}
        return await self.invoke_with_try(query, json)

    async def get_facets(self) -> stratz.FacetsResponse:
        """Queries Dota 2 Hero Facet Constants."""
        query = """
query FacetConstants {
    constants {
        facets {
            id
            name
            color
            icon
            language {
                displayName
            }
            gradientId
        }
    }
}"""
        json = {"query": query}
        return await self.invoke_with_try(query, json)


if __name__ == "__main__":
    import asyncio

    # OPENDOTA
    async def test_opendota_get_match() -> None:
        async with OpenDotaClient() as opendota_client:
            match = await opendota_client.get_match(match_id=7543594334)

            for item in ["players", "teamfights", "radiant_xp_adv", "radiant_gold_adv", "picks_bans"]:
                match.pop(item, None)

        print(opendota_client.rate_limiter.rate_limits_string)  # noqa: T201

    async def test_opendota_request_parse() -> None:
        async with OpenDotaClient() as opendota_client:
            await opendota_client.request_parse(match_id=7543594334)

    # STRATZ
    async def test_stratz_get_match() -> None:
        async with StratzClient() as stratz_client:
            match_id = 7549006442
            friend_id = 159020918
            match = await stratz_client.get_fpc_match_to_edit(match_id=match_id, friend_id=friend_id)
            print(match["data"]["match"]["players"][0]["item3Id"])  # noqa: T201

        print(stratz_client.rate_limiter.rate_limits_string)  # noqa: T201

    async def test_stratz_get_heroes() -> None:
        async with StratzClient() as stratz_client:
            heroes = await stratz_client.get_heroes()
            print(heroes["data"]["constants"]["heroes"][2])  # noqa: T201

        print(stratz_client.rate_limiter.rate_limits_string)  # noqa: T201

    # STEAM WEB API
    async def test_steam_web_api_client() -> None:
        async with SteamWebAPIClient() as steam_web_api:
            match = await steam_web_api.get_match_details(7566292740)
            print(match)  # noqa: T201

    asyncio.run(test_stratz_get_heroes())
