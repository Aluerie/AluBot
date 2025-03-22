from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Annotated

import discord
from discord.ext import commands

from bot import AluCog
from utils import const, errors, times

if TYPE_CHECKING:
    from bot import AluBot, AluGuildContext


class Moderation(AluCog):
    """Commands to moderate servers with."""

    def member_check(self, member: discord.Member) -> None:
        if member.id == self.bot.owner_id:
            msg = f"You can't do that to Aluerie {const.Emote.bubuGun}"
            raise errors.ErroneousUsage(msg)
        if member.bot:
            msg = "Don't bully bots, please"
            raise errors.ErroneousUsage(msg)

    @commands.has_role(const.Role.discord_mods)
    # @app_commands.guilds(const.Guild.community)
    @commands.command()
    async def warn(self, ctx: AluGuildContext, member: discord.Member, *, reason: str = "No reason") -> None:
        """Give member a warning.

        Doesn't do anything besides that.

        Parameters
        ----------
        member: discord.Member
            Member to warn.
        reason: str = "No reason"
            Reason for the warning.
        """
        self.member_check(member)

        embed = (
            discord.Embed(
                color=const.Palette.red(shade=300),
                title="Manual warning by a mod",
            )
            .add_field(name="Reason", value=reason)
            .set_author(name=member.display_name, icon_url=member.display_avatar.url)
            .set_thumbnail(url=discord.PartialEmoji.from_str(const.Emote.peepoYellowCard).url)
            .set_footer(text=f"Warned by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        )
        message = await ctx.reply(embed=embed)
        embed.url = message.jump_url
        await self.community.logs.send(embed=embed)

    @commands.has_role(const.Role.discord_mods)
    # @app_commands.guilds(const.Guild.community)
    @commands.command()
    async def mute(
        self,
        ctx: AluGuildContext,
        member: discord.Member,
        *,
        until_when_and_reason: Annotated[
            times.FriendlyTimeResult,
            times.UserFriendlyTime(commands.clean_content, default="..."),
        ],
    ) -> None:
        """Give member a mute."""
        self.member_check(member)

        dt, reason = until_when_and_reason.dt, until_when_and_reason.arg
        days_out = dt - discord.utils.utcnow()
        if days_out <= datetime.timedelta(days=28):
            try:
                await member.edit(timed_out_until=dt, reason=reason)
            except discord.HTTPException as exc:
                e = (
                    discord.Embed(
                        color=const.Color.error,
                        title="Oups... Error during muting.",
                        description="If you think it's wrong then contact Aluerie.",
                    )
                    .set_author(name=str(member), icon_url=member.display_avatar.url)
                    .add_field(name="Error Message", value=f"```py\n{exc.text}\n```")
                    .set_footer(text=f"Member ID: {member.id}")
                )
                await ctx.reply(embed=e)
                return
        else:
            msg = "Discord does not allow muting people for more than 28 days."
            raise errors.BadArgument(msg)

        e = discord.Embed(title="Manual mute by a mod", color=const.Palette.red(shade=600), description=reason)
        e.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        e.set_footer(text=f"Muted by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        e.set_thumbnail(url=discord.PartialEmoji.from_str(const.Emote.peepoRedCard).url)
        e.add_field(name="Muted Until", value=discord.utils.format_dt(dt, style="R"))
        e.add_field(name="Reason", value=reason)
        msg = await ctx.reply(embed=e)
        e.url = msg.jump_url
        await self.community.logs.send(embed=e)

    @commands.Cog.listener(name="on_member_update")
    async def log_mutes(self, before: discord.Member, after: discord.Member) -> None:
        """Log mutes into #logs channel."""
        if after.guild.id != const.Guild.community:
            return

        if after.timed_out_until and before.is_timed_out() is False and after.is_timed_out() is True:
            # member is muted

            mute_actor_str = "Unknown"
            async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_update):
                target: discord.Member = entry.target  # type: ignore[reportAssignmentType]
                user: discord.Member = entry.target  # type: ignore[reportAssignmentType]
                if target.id == after.id and entry.after.timed_out_until == after.timed_out_until:
                    mute_actor_str = user.name

            embed = discord.Embed(
                color=discord.Color.red(),
                description=discord.utils.format_dt(after.timed_out_until, style="R"),
            ).set_author(
                name=f"{after.display_name} is muted by {mute_actor_str} until",
                icon_url=after.display_avatar.url,
            )
            await self.community.logs.send(embed=embed)

        # elif before.is_timed_out() is True and after.is_timed_out() is False:
        #     # member is unmuted
        #     return
        # apparently discord limitation -> it does not ever happen

    @commands.Cog.listener("on_guild_channel_create")
    async def give_aluerie_all_perms(self, channel: discord.abc.GuildChannel) -> None:
        """Give Aluerie All Permissions in the channel.

        Just an extra step to avoid some headache because my main acount is not an administrator in my own server.
        """
        if channel.guild.id != self.community.id:
            return

        all_perms = discord.PermissionOverwrite.from_pair(
            allow=discord.Permissions.all(),
            deny=discord.Permissions.none(),
        )
        reason = "Give all permissions to Aluerie"
        await channel.set_permissions(self.community.sister_of_the_veil, overwrite=all_perms, reason=reason)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Moderation(bot))
