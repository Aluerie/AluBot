from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils.formats import block_function
from utils.links import move_link_to_title, replace_tco_links
from utils.var import Cid

from ._base import LoLNewsBase

if TYPE_CHECKING:
    from utils.bot import AluBot


class CopypasteLeague(LoLNewsBase):

    blocked_words = [
        'Free Champion Rotation',
        'PlayRuneterra',
        'RiotForge',
        'TFT',
        'Teamfight Tactics',
        'Mortdog',
        'Champion & Skin Sale',
        'Champion &amp; Skin Sale',
        'prime gaming',
        'wildrift',
        'Wild Rift',
        'entwuhoo',  # tft dev account
        'RiotExis',  # legends of runeterra
        'RiotZephyreal',  # merch
        'davetron',  # LoR
        'infinitystudioc',  # merch
    ]

    whitelist_words = [
        # ' Notes',
    ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.channel.id == Cid.copylol_ff20:
                if block_function(message.content, self.blocked_words, self.whitelist_words):
                    return

                embeds = None
                content = message.content
                if "https://twitter.com" in message.content:
                    await asyncio.sleep(2)
                    #  answer = await msg.channel.fetch_message(int(msg.id))
                    embeds = [await replace_tco_links(self.bot.session, item) for item in message.embeds]
                    embeds = [move_link_to_title(embed) for embed in embeds]
                    content = ''

                files = [await item.to_file() for item in message.attachments]
                message = await self.news_channel.send(content=content, embeds=embeds, files=files)
                await message.publish()
        except Exception as error:
            await self.bot.send_traceback(error, where='LoL news copypaste')


async def setup(bot: AluBot):
    await bot.add_cog(CopypasteLeague(bot))
