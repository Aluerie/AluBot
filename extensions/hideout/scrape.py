from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import discord
from bs4 import BeautifulSoup

from utils import aluloop, const

from ._base import HideoutCog

if TYPE_CHECKING:
    pass


class LeagueOfLegendsPatchChecker(HideoutCog):
    async def cog_load(self) -> None:
        self.patch_checker.start()

    async def cog_unload(self) -> None:
        self.patch_checker.cancel()

    @aluloop(minutes=20)
    async def patch_checker(self):
        # somewhat credits to
        # https://github.com/Querijn/BottyMcBotface/blob/master/src/VersionChecker.ts
        # but really there is only two json links to get info from.

        # they keep patch related data in the following json's that we can pool
        patch_news_url = 'https://www.leagueoflegends.com/page-data/en-us/news/tags/patch-notes/page-data.json'

        async with self.bot.session.get(patch_news_url) as r_news:
            page_data = await r_news.json()

        # it's something like '/news/game-updates/patch-13-22-notes/'
        new_patch_href = page_data['result']['data']['articles']['nodes'][0]['url']['url']

        query = """ UPDATE botvars
                    SET lol_patch=$1
                    WHERE lol_patch IS DISTINCT FROM $1
                    RETURNING True
                """
        is_patch_new: None | Literal[True] = await self.bot.pool.fetchval(query, new_patch_href)
        if not is_patch_new:
            return

        latest_patch_data_url = f'https://www.leagueoflegends.com/page-data/en-us{new_patch_href}page-data.json'
        async with self.bot.session.get(latest_patch_data_url) as r_patch_data:
            node = (await r_patch_data.json())["result"]["data"]["all"]["nodes"][0]
            html_data = node["patch_notes_body"][0]["patch_notes"]['html']
            patch_soup = BeautifulSoup(html_data, 'html.parser')

        try:
            patch_highlights_image_url: str = (
                patch_soup.find('h2', id='patch-patch-highlights')
                .find_next('a')  # type: ignore
                .get('href')  # type: ignore
            )
            files = [await self.bot.imgtools.url_to_file(patch_highlights_image_url)]
        except:
            # means we got None in somewhere above instead of a proper url.
            files = []

        e = discord.Embed(title=node["title"], colour=const.Colour.rspbrry())
        e.url = f'https://www.leagueoflegends.com/en-us{new_patch_href}'
        # e.set_image(url=img_url)
        e.set_thumbnail(url=node["banner"]["url"])
        e.set_author(name='League of Legends', icon_url=const.Logo.lol)
        await self.bot.hideout.repost.send(embed=e, files=files)


async def setup(bot):
    await bot.add_cog(LeagueOfLegendsPatchChecker(bot))
