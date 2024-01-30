from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence

import discord
from discord.ext import commands

from utils import const

from ._base import ConfigGuildCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluGuildContext


class Prefix(ConfigGuildCog, name="Server settings for the bot", emote=const.Emote.PepoBeliever):
    """Change bot\'s config for the server

    More to come.
    """

    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(view_audit_log=True)
    async def turn_emote_logs(self, ctx: AluGuildContext, channel: Optional[discord.TextChannel] = None):
        """Turn emote logs on in this channel for this guild"""
        ch = channel or ctx.channel

        query = "UPDATE guilds SET emote_logs_id=$1 WHERE id=$2"
        await self.bot.pool.execute(query, ch.id, ctx.guild.id)

        e = discord.Embed(title="Emote logging is turned on", colour=const.Colour.blueviolet)
        e.description = f"Now I will log emote create/delete/rename actions in {ch.mention}. Go try it!"
        e.set_footer(text=f"With love, {ctx.guild.me.display_name}")
        e.set_thumbnail(url=ctx.guild.me.display_avatar.url)
        await ctx.reply(embed=e)

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: discord.Guild,
        before: Sequence[discord.Emoji],
        after: Sequence[discord.Emoji],
    ):
        query = "SELECT emote_logs_id FROM guilds WHERE id=$1"
        val = await self.bot.pool.fetchval(query, guild.id)
        ch = self.bot.get_channel(val)
        if ch is None:
            return

        diff_after = [x for x in after if x not in before]
        diff_before = [x for x in before if x not in after]

        async def set_author(emotion, embedx: discord.Embed, act: discord.AuditLogAction):
            if emotion.managed:
                embedx.set_author(name="Tw.tv Sub integration", icon_url=const.Logo.Twitch)
                return
            else:
                async for entry in guild.audit_logs(action=act):
                    if entry.target.id == emotion.id:
                        embedx.set_author(name=entry.user.name, icon_url=entry.user.display_avatar.url)
                        return

        # Remove emote ###########################################################################
        if diff_after == [] and diff_before != []:
            for emote in diff_before:
                if not emote.managed and guild.id == const.Guild.community:
                    query = "DELETE FROM emotes WHERE id=$1"
                    await self.bot.pool.execute(query, emote.id)
                e = discord.Embed(title=f"`:{emote.name}:` emote removed", colour=0xB22222)
                e.description = f"[Image link]({emote.url})"
                e.set_thumbnail(url=emote.url)
                await set_author(emote, e, discord.AuditLogAction.emoji_delete)
                await ch.send(embed=e)
        # Add emote ###############################################################################
        elif diff_after != [] and diff_before == []:
            for emote in diff_after:
                e = discord.Embed(title=f"`:{emote.name}:` emote created", colour=0x00FF7F)
                e.description = f"[Image link]({emote.url})"
                e.set_thumbnail(url=emote.url)
                await set_author(emote, e, discord.AuditLogAction.emoji_create)
                await ch.send(embed=e)
                if not emote.managed:
                    msg = await ch.send("{0} {0} {0}".format(str(emote)))
                    await msg.add_reaction(str(emote))
                if guild.id == const.Guild.community:
                    query = "INSERT INTO emotes (id, name, animated) VALUES ($1, $2, $3)"
                    await self.bot.pool.execute(query, emote.id, str(emote), emote.animated)
        # Renamed emote ###########################################################################
        else:
            diff_after_name = [x for x in after if x.name not in [x.name for x in before]]
            diff_before_name = [x for x in before if x.name not in [x.name for x in after]]
            for emote_after, emote_before in zip(diff_after_name, diff_before_name):
                if not emote_after.managed and guild.id == const.Guild.community:
                    query = "UPDATE emotes SET name=$1 WHERE id=$2"
                    await self.bot.pool.execute(query, str(emote_after), emote_after.id)
                e = discord.Embed(colour=0x1E90FF, description=f"[Image link]({emote_after.url})")
                replaced_or_renamed_word = "replaced by" if emote_after.managed else "renamed into"
                e.title = f"`:{emote_before.name}:` emote {replaced_or_renamed_word} `:{emote_after.name}:`"
                e.set_thumbnail(url=emote_after.url)
                await set_author(emote_after, e, discord.AuditLogAction.emoji_update)
                await ch.send(embed=e)


async def setup(bot: AluBot):
    await bot.add_cog(Prefix(bot))
