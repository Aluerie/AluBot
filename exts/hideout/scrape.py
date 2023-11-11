from __future__ import annotations

from typing import TYPE_CHECKING

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
        # they keep patch related data in the following json's that we can pool
        url = 'https://www.leagueoflegends.com/page-data/en-us/news/tags/patch-notes/page-data.json'

        async with self.bot.session.get(url) as resp:
            page_data = await resp.json()

        # it's something like '/news/game-updates/patch-13-22-notes/'
        new_patch_href = page_data['result']['data']['articles']['nodes'][0]['url']['url']

        query = """ UPDATE botinfo
                    SET lol_patch=$1
                    WHERE id=$2
                    AND lol_patch IS DISTINCT FROM $1
                    RETURNING True
                """
        val = await self.bot.pool.fetchval(query, new_patch_href, const.Guild.community)
        if not val:
            return

        patch_url = f'https://www.leagueoflegends.com{new_patch_href}'

        # we could try getting fancy data like patch highlights from
        # https://www.leagueoflegends.com/page-data/en-us/news/game-updates/patch-13-22-notes/page-data.json
        # but they also keep everything in html string
        # so it doesn't really matter, I guess?
        # but here we can get meta tags
        async with self.bot.session.get(patch_url) as resp:
            patch_soup = BeautifulSoup(await resp.read(), 'html.parser')
        metas = patch_soup.find_all('meta')

        def content_if_property(html_property: str):
            for meta in metas:
                if meta.attrs.get('property', None) == html_property:
                    return meta.attrs.get('content', None)
            return None

        # maybe use ('a' ,{'class': 'skins cboxElement'})
        img_url = patch_soup.find('h2', id='patch-patch-highlights').find_next('a').get('href')  # type: ignore
        e = discord.Embed(title=content_if_property('og:title'), url=patch_url, colour=const.Colour.rspbrry())
        e.description = content_if_property("og:description")
        e.set_image(url=img_url)
        e.set_thumbnail(url=content_if_property('og:image'))
        e.set_author(name='League of Legends', icon_url=const.Logo.lol)
        await self.bot.hideout.repost.send(embed=e)


async def setup(bot):
    await bot.add_cog(LeagueOfLegendsPatchChecker(bot))
