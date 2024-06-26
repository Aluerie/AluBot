from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, TypedDict, override

import discord
from bs4 import BeautifulSoup
from discord.ext import commands

from utils import aluloop, const

from ._base import HideoutCog

if TYPE_CHECKING:
    from bot import AluBot, Timer

    class LeaguePatchCheckTimerData(TypedDict):
        last_patch_href: str


class LeagueOfLegendsPatchChecker(HideoutCog):
    # somewhat credits to
    # https://github.com/Querijn/BottyMcBotface/blob/master/src/VersionChecker.ts
    # but really there is only two json links to get info from.

    patch_news_json = "https://www.leagueoflegends.com/page-data/en-us/news/tags/patch-notes/page-data.json"
    # Botty is using different link though:
    # it's trying to pull from
    # https://www.leagueoflegends.com/page-data/en-us/news/game-updates/patch-${nextMajor.toString()}-${nextMinor.toString()}-notes/page-data.json
    # i.e. https://www.leagueoflegends.com/page-data/en-us/news/game-updates/patch-14-11-notes/page-data.json

    @override
    async def cog_load(self) -> None:
        self.initiate_league_patch_check_timer.start()

    @override
    async def cog_unload(self) -> None:
        self.initiate_league_patch_check_timer.cancel()

    @aluloop(count=1)
    async def initiate_league_patch_check_timer(self) -> None:
        # we have to do this quirk bcs if we put this into cog load
        # it will not have TimerManager initiated yet.
        query = "SELECT id FROM timers WHERE event = $1"
        value = await self.bot.pool.fetchval(query, "league_patch_check")
        if value:
            # the timer already exists
            return

        # the timer does not exist so we create it (again)
        # probably cog wasn't loaded when event fired
        # which is actually not addressed in the TimerManager logic...
        now = datetime.datetime.now(datetime.UTC)
        data: LeaguePatchCheckTimerData = {"last_patch_href": "none"}
        await self.bot.create_timer(
            event="league_patch_check",
            expires_at=now + datetime.timedelta(minutes=20),
            data=data,
        )

    @commands.Cog.listener("on_league_patch_check_timer_complete")
    async def league_patch_checker(self, timer: Timer[LeaguePatchCheckTimerData]) -> None:
        last_patch_href = timer.data["last_patch_href"]

        async with self.bot.session.get(self.patch_news_json) as r_news:
            page_data = await r_news.json()
            newest_patch_href = page_data["result"]["data"]["articles"]["nodes"][0]["url"]["url"]
            # ^^^ it's something like '/news/game-updates/patch-13-22-notes/'
            if newest_patch_href == last_patch_href:
                sleep_time = datetime.timedelta(minutes=30)
            else:
                # new patch is here
                # thus we are somewhat sure next ~12.5 days gonna be patch-less
                sleep_time = datetime.timedelta(days=12, hours=20)
                await self.send_league_patch_notification(newest_patch_href)

        await self.bot.create_timer(
            event=timer.event,
            expires_at=timer.expires_at + sleep_time,
            data={"last_patch_href": newest_patch_href},
        )

    async def send_league_patch_notification(self, newest_patch_href: str) -> None:
        latest_patch_data_url = f"https://www.leagueoflegends.com/page-data/en-us{newest_patch_href}page-data.json"
        async with self.bot.session.get(latest_patch_data_url) as r_patch_data:
            node = (await r_patch_data.json())["result"]["data"]["all"]["nodes"][0]
            html_data = node["patch_notes_body"][0]["patch_notes"]["html"]
            patch_soup = BeautifulSoup(html_data, "html.parser")

        try:
            patch_highlights_image_url: str = (
                patch_soup.find("h2", id="patch-patch-highlights")
                .find_next("a")  # type: ignore
                .get("href")  # type: ignore
            )
            files = [await self.bot.transposer.url_to_file(patch_highlights_image_url)]
        except:
            # means we got None in somewhere above instead of a proper url.
            # and need to investigate why
            files = []

        embed = (
            discord.Embed(
                colour=const.Colour.darkslategray,
                title=node["title"],
                url=f"https://www.leagueoflegends.com/en-us{newest_patch_href}",
            )
            .set_author(name="League of Legends", icon_url=const.Logo.Lol)
            .set_thumbnail(url=node["banner"]["url"])
        )
        await self.bot.hideout.repost.send(embed=embed, files=files)


async def setup(bot: AluBot) -> None:
    pass  # fok league patches
    # await bot.add_cog(LeagueOfLegendsPatchChecker(bot))
