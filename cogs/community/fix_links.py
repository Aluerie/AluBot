from __future__ import annotations

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
            await mimic.send_user_message(message.author, message=message, new_content=fixed_links)
            await message.delete()
        except:
            return


async def setup(bot):
    await bot.add_cog(FixLinksCommunity(bot))
