from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from cogs.utilities.fix_links import fix_link_worker
from utils import AluCog, const, webhook

if TYPE_CHECKING:
    pass


class FixLinksCommunity(AluCog):
    @commands.Cog.listener('on_message')
    async def fix_links(self, message: discord.Message):
        if not message.guild:
            return
        elif message.guild.id not in const.MY_GUILDS:
            return
        if message.author.bot:
            return

        fixed_links = fix_link_worker(message.content)
        if not fixed_links:
            return

        try:
            mimic = webhook.MimicUserWebhook.from_message(bot=self.bot, message=message)
            msg = await mimic.send_user_message(message.author, message=message, new_content=fixed_links, wait=True)
            await message.delete()
            await asyncio.sleep(1)

            # Okay discord is a bit stupid and does not allow hyperlinks from website embeds
            # this is why I will have to do the job myself.
            links = []
            colour = const.Colour.pink()
            for e in msg.embeds:
                e = e.copy()
                links += re.findall(const.REGEX_URL_LINK, str(e.description))
                colour = e.colour

            if links:
                e = discord.Embed(color=colour)
                e.description = '\n'.join(links)
                await mimic.send_user_message(message.author, embed=e)
            
        except Exception as err:
            print(err)


async def setup(bot):
    await bot.add_cog(FixLinksCommunity(bot))
