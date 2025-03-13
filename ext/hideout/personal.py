from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from bot import AluCog
from utils import const

if TYPE_CHECKING:
    import discord

    from bot import AluBot


class HideoutPersonal(AluCog):
    @commands.Cog.listener(name="on_message")
    async def personal_git_copy_paste(self, message: discord.Message) -> None:
        """Cringe moment, sends."""
        if message.channel.id == const.Channel.alubot_github:
            # Send me discord notifications when somebody except me or dependabot
            # spams my repository with updates
            embeds = [e.copy() for e in message.embeds]

            for e in embeds:
                if e.author and e.author.name not in {self.bot.developer, "dependabot[bot]"}:
                    await self.hideout.repost.send(embeds=embeds)
                    break

        elif message.channel.id == const.Channel.steamdb_news:
            # yoink pushed N commits messages from the Steam Tracker
            if message.embeds and message.embeds[0].title and "pushed" in message.embeds[0].title:
                embed = message.embeds[0].copy()
                await self.hideout.repost.send(embed=embed)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(HideoutPersonal(bot))
