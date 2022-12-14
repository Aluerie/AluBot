from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence

from discord import AuditLogAction, Embed, TextChannel
from discord.ext import commands

from .utils.checks import is_guild_owner
from .utils.var import Clr, Ems, Sid, Img

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import Context
    from discord import Guild, Emoji


class Prefix(commands.Cog, name='Settings for the bot'):
    """
    Change bot's config for the server

    More to come.
    """
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.help_emote = Ems.PepoBeliever

    @is_guild_owner()
    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx: Context):
        """Get a prefix for this server"""
        prefix = self.bot.prefixes.get(ctx.guild.id)
        if prefix is None:
            prefix = '$'
        em = Embed(description=f'Currently, prefix for this server is `{prefix}`', colour=Clr.prpl)
        em.set_footer(text='To change prefix use `@AluBot prefix set` command')
        await ctx.reply(embed=em)

    @is_guild_owner()
    @prefix.command()
    async def set(self, ctx: Context, *, new_prefix: str):
        """
        Set new prefix for the server.
        If you have troubles to set a new prefix because other bots also answer it then \
        just mention the bot with the command `@AluBot prefix set`.
        Spaces are not allowed in the prefix.
        """
        if len(new_prefix.split()) > 1:
            raise commands.BadArgument(
                'Space usage is not allowed in `prefix set` command'
            )
        if new_prefix == '$':
            await self.bot.prefixes.remove(ctx.guild.id)
            em = Embed(description='Successfully reset prefix to our default `$` sign', colour=Clr.prpl)
        else:
            await self.bot.prefixes.put(ctx.guild.id, new_prefix)
            em = Embed(description=f'Changed this server prefix to `{new_prefix}`', colour=Clr.prpl)
        await ctx.reply(embed=em)

    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(view_audit_log=True)
    async def turn_emote_logs(self, ctx: Context, channel: Optional[TextChannel] = None):
        """Turn emote logs on in this channel for this guild"""
        ch = channel or ctx.channel

        query = 'UPDATE guilds SET emote_logs_id=$1 WHERE id=$2'
        await self.bot.pool.execute(query, ch.id, ctx.guild.id)

        em = Embed(title='Emote logging is turned on', colour=Clr.prpl)
        em.description = f'Now I will log emote create/delete/rename actions in {ch.mention}. Go try it!'
        em.set_footer(text=f'With love, {ctx.guild.me.display_name}')
        em.set_thumbnail(url=ctx.guild.me.display_avatar.url)
        await ctx.reply(embed=em)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: Guild, before: Sequence[Emoji], after: Sequence[Emoji]):
        query = 'SELECT emote_logs_id FROM guilds WHERE id=$1'
        val = await self.bot.pool.fetchval(query, guild.id)
        ch = self.bot.get_channel(val)
        if ch is None:
            return

        diff_after = [x for x in after if x not in before]
        diff_before = [x for x in before if x not in after]

        async def set_author(emotion, embedx: Embed, act):
            if emotion.managed:
                embedx.set_author(name='Tw.tv Sub integration', icon_url=Img.twitchtv)
                return
            else:
                async for entry in guild.audit_logs(action=act):
                    if entry.target.id == emotion.id:
                        embedx.set_author(name=entry.user.name, icon_url=entry.user.display_avatar.url)
                        return

        # Remove emote ###########################################################################
        if diff_after == [] and diff_before != []:
            for emote in diff_before:
                if not emote.managed and guild.id == Sid.alu:
                    query = 'DELETE FROM emotes WHERE id=$1'
                    await self.bot.pool.execute(query, emote.id)
                em = Embed(title=f'`:{emote.name}:` emote removed', colour=0xb22222)
                em.description = f'[Image link]({emote.url})'
                em.set_thumbnail(url=emote.url)
                await set_author(emote, em, AuditLogAction.emoji_delete)
                await ch.send(embed=em)
        # Add emote ###############################################################################
        elif diff_after != [] and diff_before == []:
            for emote in diff_after:
                em = Embed(title=f'`:{emote.name}:` emote created', colour=0x00ff7f)
                em.description = f'[Image link]({emote.url})'
                em.set_thumbnail(url=emote.url)
                await set_author(emote, em, AuditLogAction.emoji_create)
                await ch.send(embed=em)
                if not emote.managed:
                    msg = await ch.send('{0} {0} {0}'.format(str(emote)))
                    await msg.add_reaction(str(emote))
                if guild.id == Sid.alu:
                    query = 'INSERT INTO emotes (id, name, animated) VALUES ($1, $2, $3)'
                    await self.bot.pool.execute(query, emote.id, str(emote), emote.animated)
        # Renamed emote ###########################################################################
        else:
            diff_after_name = [x for x in after if x.name not in [x.name for x in before]]
            diff_before_name = [x for x in before if x.name not in [x.name for x in after]]
            for emote_after, emote_before in zip(diff_after_name, diff_before_name):
                if not emote_after.managed and guild.id == Sid.alu:
                    query = 'UPDATE emotes SET name=$1 WHERE id=$2'
                    await self.bot.pool.execute(query, emote_after.id, str(emote_after))
                em = Embed(colour=0x1e90ff, description=f'[Image link]({emote_after.url})')
                replaced_or_renamed_word = "replaced by" if emote_after.managed else "renamed into"
                em.title = f'`:{emote_before.name}:` emote {replaced_or_renamed_word} `:{emote_after.name}:`'
                em.set_thumbnail(url=emote_after.url)
                await set_author(emote_after, em, AuditLogAction.emoji_update)
                await ch.send(embed=em)


async def setup(bot: AluBot):
    await bot.add_cog(Prefix(bot))
