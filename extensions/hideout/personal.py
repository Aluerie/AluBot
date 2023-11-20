from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import const

from ._base import HideoutCog

if TYPE_CHECKING:
    from bot import AluBot


class PersonalCommands(HideoutCog):
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild == self.bot.hideout.guild:  # and member.bot:
            # if somebody somehow enters it then also jail them lol
            await member.add_roles(self.bot.hideout.jailed_bots)

    @commands.Cog.listener(name="on_message")
    async def personal_git_copy_paste(self, message: discord.Message):
        if message.channel.id == const.Channel.github_webhook:
            embeds = [e.copy() for e in message.embeds]

            for e in embeds:
                if e.author and e.author.name not in [self.bot.developer, "dependabot[bot]"]:
                    await self.hideout.repost.send(embeds=embeds)
                    break


async def setup(bot: AluBot):
    await bot.add_cog(PersonalCommands(bot))
