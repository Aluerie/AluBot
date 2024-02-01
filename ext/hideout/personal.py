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
            # Send me discord notifications when somebody except me or dependabot
            # spams my repository with updates
            embeds = [e.copy() for e in message.embeds]

            for e in embeds:
                if e.author and e.author.name not in [self.bot.developer, "dependabot[bot]"]:
                    await self.hideout.repost.send(embeds=embeds)
                    break

        elif message.channel.id == const.Channel.steamdb_news:
            # yoink pushed N commits messages from the Steam Tracker
            if message.embeds and message.embeds[0].title and "pushed" in message.embeds[0].title:
                embed = message.embeds[0].copy()
                await self.hideout.repost.send(embed=embed)


async def setup(bot: AluBot):
    await bot.add_cog(PersonalCommands(bot))
