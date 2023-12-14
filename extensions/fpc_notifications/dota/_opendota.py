from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, Optional, Union

if TYPE_CHECKING:
    from bot import AluBot


__all__ = ("OpendotaRequestMatch",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class OpendotaNotOK(Exception):
    pass


class OpendotaMatchNotParsed(Exception):
    pass


class OpendotaTooManyFails(Exception):
    pass


class OpendotaRequestMatch:
    def __init__(self, match_id: int, job_id: Optional[int] = None):
        self.match_id = match_id
        self.job_id: Optional[int] = job_id

        self.fails = 0
        self.tries = 0
        self.parse_attempts = 0

        self.is_first_loop_skipped = False
        self.dict_ready = False
        self.api_calls_done = 0

    def __repr__(self) -> str:
        return (
            f"<OpendotaRequestMatch match_id={self.match_id} "
            f"fails/tries/parse={self.fails}/{self.tries}/{self.parse_attempts} ready={self.dict_ready}>"
        )

    async def post_request(self, bot: AluBot) -> int:
        """
        Make opendota request parsing API call
        @return job_id as integer or False in case of not ok response
        """
        async with bot.session.post(f"https://api.opendota.com/api/request/{self.match_id}") as resp:
            log.debug(f"OK: {resp.ok} json: {await resp.json()} " f"tries: {self.tries} fails: {self.fails}")
            bot.update_odota_ratelimit(resp.headers)
            self.api_calls_done += 1
            if resp.ok:
                try:
                    return (await resp.json())["job"]["jobId"]
                except:
                    return 0  # idk opendota sometimes returns {} as json answer
            else:
                raise OpendotaNotOK("POST /request response was not OK")

    async def get_request(self, bot: AluBot) -> Union[dict, Literal[False]]:
        """
        Make opendota request parsing API call
        @return job_id as integer or False in case of not ok response
        @raise OpendotaNotOK
        """
        async with bot.session.get(f"https://api.opendota.com/api/request/{self.job_id}") as resp:
            log.debug(
                f"OK: {resp.ok} json: {await resp.json()} job_id: {self.job_id} "
                f"tries: {self.tries} fails: {self.fails}"
            )
            bot.update_odota_ratelimit(resp.headers)
            self.api_calls_done += 1
            if resp.ok:
                return await resp.json()
            else:
                raise OpendotaNotOK("GET /request response was not OK")

    async def get_matches(self, bot: AluBot) -> dict:
        """Make opendota request match data API call"""
        async with bot.session.get(f"https://api.opendota.com/api/matches/{self.match_id}") as resp:
            log.debug(
                f"OK: {resp.ok} match_id: {self.match_id} job_id: {self.job_id} "
                f"tries: {self.tries} fails: {self.fails}"
            )
            bot.update_odota_ratelimit(resp.headers)
            self.api_calls_done += 1
            if resp.ok:
                d = await resp.json()
                if d["players"][0]["purchase_log"]:
                    self.dict_ready = True
                    return d["players"]
                else:
                    raise OpendotaMatchNotParsed("GET /matches returned not fully parsed match")
            else:
                raise OpendotaNotOK("GET /matches response was not OK")

    async def workflow(self, bot: AluBot) -> Union[dict, None]:
        if self.fails > 10 or self.parse_attempts > 10:
            raise OpendotaTooManyFails("We failed too many times")
        elif not self.is_first_loop_skipped:
            self.is_first_loop_skipped = True
        elif not self.job_id:
            if self.tries >= pow(3, self.fails) - 1:
                try:
                    self.job_id = await self.post_request(bot)
                    query = "UPDATE dota_matches SET opendota_jobid=$1 WHERE match_id=$2"
                    await bot.pool.execute(query, self.job_id, self.match_id)
                    self.tries, self.fails = 0, 0
                except OpendotaNotOK:
                    self.fails += 1
            else:
                self.tries += 1
        else:
            if self.tries >= pow(3, self.fails) - 1:
                try:
                    return await self.get_matches(bot)
                except OpendotaMatchNotParsed:
                    self.job_id = None
                    self.parse_attempts += 1
                    self.tries, self.fails = 0, 0
                except OpendotaNotOK:
                    self.fails += 1
            else:
                self.tries += 1
