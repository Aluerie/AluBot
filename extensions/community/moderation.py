from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Annotated

import discord
from discord.ext import commands

from utils import AluGuildContext, checks, const, errors, times

from ._base import CommunityCog

if TYPE_CHECKING:
    from utils import AluBot


class ModerationCog(CommunityCog, emote=const.Emote.peepoPolice):
    """Commands to moderate servers with"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def warn_check(self, member: discord.Member):
        if member.id == self.bot.owner_id:
            raise errors.ErroneousUsage(f"You can't do that to Aluerie {const.Emote.bubuGun}")
        if member.bot:
            raise errors.ErroneousUsage("Don't bully bots, please")

    @commands.has_role(const.Role.discord_mods)
    @checks.prefix.is_community()
    @commands.command()
    async def warn(self, ctx: AluGuildContext, member: discord.Member, *, reason: str = "No reason"):
        """Give member a warning."""
        self.warn_check(member)

        e = discord.Embed(title="Manual warning by a mod", colour=const.MaterialPalette.red(shade=300))
        e.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        e.set_footer(text=f"Warned by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        e.set_thumbnail(url=discord.PartialEmoji.from_str(const.Emote.peepoYellowCard).url)
        e.add_field(name='Reason', value=reason)
        msg = await ctx.reply(embed=e)
        e.url = msg.jump_url
        await self.community.logs.send(embed=e)

    @commands.has_role(const.Role.discord_mods)
    @checks.prefix.is_community()
    @commands.command()
    async def mute(
        self,
        ctx: AluGuildContext,
        member: discord.Member,
        *,
        until_when_and_reason: Annotated[
            times.FriendlyTimeResult, times.UserFriendlyTime(commands.clean_content, default='...')
        ],
    ):
        """Give member a mute."""
        self.warn_check(member)

        dt, reason = until_when_and_reason.dt, until_when_and_reason.arg
        days_out = dt - discord.utils.utcnow()
        if days_out <= datetime.timedelta(days=28):
            try:
                await member.edit(timed_out_until=dt, reason=reason)
            except discord.HTTPException as exc:
                e = discord.Embed(colour=const.Colour.error(), title='Oups... Error during muting.')
                e.set_author(name=str(member), icon_url=member.display_avatar.url)
                e.set_footer(text=f'Member ID: {member.id}')
                e.description = 'If you think it\'s wrong then contact Aluerie.'
                e.add_field(name='Error Message', value=f'```py\n{exc.text}\n```')
                return await ctx.reply(embed=e)
        else:
            raise errors.BadArgument('Discord does not allow muting people for more than 28 days.')

        e = discord.Embed(title="Manual mute by a mod", colour=const.MaterialPalette.red(shade=600), description=reason)
        e.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        e.set_footer(text=f"Muted by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        e.set_thumbnail(url=discord.PartialEmoji.from_str(const.Emote.peepoRedCard).url)
        e.add_field(name='Muted Until', value=discord.utils.format_dt(dt, style="R"))
        e.add_field(name='Reason', value=reason)
        msg = await ctx.reply(embed=e)
        e.url = msg.jump_url
        await self.community.logs.send(embed=e)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.guild.id != const.Guild.community:
            return

        if after.timed_out_until and before.is_timed_out() is False and after.is_timed_out() is True:  # member is muted
            e = discord.Embed(colour=discord.Colour.red())
            e.description = discord.utils.format_dt(after.timed_out_until, style="R")

            mute_actor_str = "Unknown"
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_update):
                target: discord.Member = entry.target  # type: ignore
                user: discord.Member = entry.target  # type: ignore
                if target.id == after.id and entry.after.timed_out_until == after.timed_out_until:
                    mute_actor_str = user.name

            author_text = f'{after.display_name} is muted by {mute_actor_str} until'
            e.set_author(name=author_text, icon_url=after.display_avatar.url)
            return await self.community.logs.send(embed=e)

        # elif before.is_timed_out() is True and after.is_timed_out() is False:  # member is unmuted
        #     return
        # apparently discord limitation -> it does not ever happen

    @commands.Cog.listener('on_guild_channel_create')
    async def give_aluerie_all_perms(self, channel: discord.abc.GuildChannel):
        if channel.guild.id != self.community.id:
            return

        sister_of_the_veil = self.community.sister_of_the_veil
        allow, deny = discord.Permissions.all(), discord.Permissions.none()
        all_perms = discord.PermissionOverwrite.from_pair(allow=allow, deny=deny)
        reason = 'Give all permissions to Aluerie'
        await channel.set_permissions(sister_of_the_veil, overwrite=all_perms, reason=reason)


async def setup(bot: AluBot):
    await bot.add_cog(ModerationCog(bot))
