from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import discord
from dateparser.search import search_dates
from discord.ext import commands

from core import AluCog
from utils import const, fmt

if TYPE_CHECKING:
    from core import AluBot

# Ignore dateparser warnings regarding pytz
warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)


class Info(AluCog, name="Info"):
    """Commands to get some useful info."""

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        parsed_dates = search_dates(message.content)
        if not parsed_dates:
            return
        for date in parsed_dates:
            dt = date[1]
            if dt.tzinfo is not None:
                e = discord.Embed(color=const.Color.prpl)
                utc_offset = o.seconds if (o := dt.utcoffset()) else 0
                dst = d.seconds if (d := dt.dst()) else 0
                e.description = (
                    f'"{date[0]}" in your timezone:\n {fmt.format_dt_tdR(dt)}\n'
                    f"{dt.tzname()} is GMT {utc_offset / 3600:+.1f}, dst: {dst / 3600:+.1f}"
                )
                await message.channel.send(embed=e)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.guild.id != const.Guild.community:
            return
        added_role = list(set(after.roles) - set(before.roles))
        removed_role = list(set(before.roles) - set(after.roles))

        async def give_text_list(role: discord.Role, channel: discord.TextChannel, msg_id: int) -> None:
            if (added_role and added_role[0] == role) or (removed_role and removed_role[0] == role):
                msg = channel.get_partial_message(msg_id)
                e = discord.Embed(title=f"List of {role.name}", color=const.Color.prpl)
                e.description = "".join([f"{member.mention}\n" for member in role.members])
                await msg.edit(content="", embed=e)

        await give_text_list(self.community.bots_role, self.community.bot_spam, 959982214827892737)
        await give_text_list(self.community.nsfw_bots_role, self.community.nsfw_bot_spam, 959982171492323388)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Info(bot))
    await bot.add_cog(StatsCommands(bot))
