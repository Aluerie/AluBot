from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord
from discord import app_commands
from discord.ext import commands
from tabulate import tabulate

from utils import const, errors, fmt, fuzzy

from ._base import BaseDevCog

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


__all__ = ("DiscordManagement",)


AMOUNT_OF_ALLOWED_GUILDS = 69


class DiscordGuildTransformer(app_commands.Transformer):
    """Discord Guild Transformer."""

    @override
    async def transform(self, interaction: AluInteraction, argument: str) -> discord.Guild:
        if argument.isdigit():
            # assume ID
            guild = discord.utils.find(lambda g: g.id == int(argument), interaction.client.guilds)
            if not guild:
                msg = f"The bot is not in the guild with id `{argument}`"
                raise errors.BadArgument(msg)
        else:
            # assume name
            guild = discord.utils.find(lambda g: g.name == argument, interaction.client.guilds)
            if not guild:
                msg = f"The bot is not in the guild with name `{argument}`"
                raise errors.BadArgument(msg)

        return guild

    @override
    async def autocomplete(self, interaction: AluInteraction, current: str) -> list[app_commands.Choice[str]]:
        guild_mapping = {f"{guild.name} ({guild.id})": guild.id for guild in interaction.client.guilds}
        keys = fuzzy.finder(current, guild_mapping.keys())
        return [app_commands.Choice(name=key, value=str(guild_mapping[key])) for key in keys][:10]


class DiscordManagement(BaseDevCog):
    """Managing the bot in Discord space.

    Mainly to control amount of the guilds the bot is in to avoid verification.
    Just in case.
    """

    def get_guild_stats(self, embed: discord.Embed, guild: discord.Guild) -> discord.Embed:
        """Prepare an embed stats about the guild."""
        embed.description = guild.description
        guild_info = tabulate(
            tabular_data=[("Name", guild.name), ("ID", guild.id), ("Shard ID", guild.shard_id or "N/A")],
            tablefmt="plain",
        )
        embed.add_field(name="Guild Info", value=fmt.code(guild_info))
        if guild.owner:
            embed.set_author(
                name=f"Owner: {guild.owner} (ID: {guild.owner_id})",
                icon_url=guild.owner.display_avatar.url,
            )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        bots = sum(m.bot for m in guild.members)
        total = guild.member_count or 1
        guild_stats = tabulate(tabular_data=[("Members", total), ("Bots", f"{bots} ({bots / total:.2%})")], tablefmt="plain")
        embed.add_field(name="Guild Stats", value=fmt.code(guild_stats))
        if guild.me:
            embed.timestamp = guild.me.joined_at
        return embed

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Send notification embed with guilds stats on `guild_join` events."""
        embed = discord.Embed(color=const.Palette.green(shade=500), title="New Guild")
        embed = self.get_guild_stats(embed, guild)
        await self.bot.hideout.global_logs.send(embed=embed)

        if len(self.bot.guilds) > AMOUNT_OF_ALLOWED_GUILDS:
            # Safe-guard to keep the bot in less than 70 guilds (I don't want verification troubles).
            await self.guild_notify(guild)
            await guild.leave()

    async def guild_notify(self, guild: discord.Guild) -> None:
        """Try to notify the guild about the bot refusing to join it due to max amount of guilds."""

        def check_channel(channel: discord.abc.GuildChannel | None) -> bool:
            """Predicate to check if we can send messages in the desired channel."""
            return (
                bool(channel)
                and not isinstance(channel, discord.ForumChannel)
                and channel.permissions_for(guild.me).send_messages
            )

        # let's try to find a #general channel or something
        # to notify the guild that the bot has to leave it
        for potential_name in ("general", "lobby"):
            channel = discord.utils.find(lambda c, n=potential_name: n in c.name, guild.channels)
            if check_channel(channel):
                break
        else:
            if check_channel(guild.system_channel):
                channel = guild.system_channel
            else:
                for ch in guild.channels:
                    if check_channel(ch):
                        channel = ch
                        break
                else:
                    # I guess we failed to find any such channel
                    return

        # we secured the type in `check_channel` but still, let's do it again
        assert channel
        assert not isinstance(channel, discord.ForumChannel | discord.CategoryChannel)
        embed = discord.Embed(
            title="I'm sorry",
            description=(
                "Even though server moderators just invited me, "
                "I have to leave this server because the bot is already in too many servers."
            ),
        ).set_footer(text="Contact @Aluerie if you really want the bot in your server, we will solve it.")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Send notification embed with guilds stats on `guild_remove` events."""
        embed = discord.Embed(color=const.Palette.red(shade=500), title="Left Guild")
        embed = self.get_guild_stats(embed, guild)
        await self.bot.hideout.global_logs.send(embed=embed)

    guild_group = app_commands.Group(
        name="guilds-dev",
        description="\N{GUITAR} Commands to manage the bot presence in Discord guilds",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @guild_group.command(name="leave")
    async def guild_leave(
        self, interaction: AluInteraction, guild: app_commands.Transform[discord.Guild, DiscordGuildTransformer]
    ) -> None:
        """🚓 Make the bot leave the guild."""
        confirm_embed = discord.Embed(
            description="Do you really want the bot to leave the following guild?",
        ).add_field(
            name="Guild Info",
            value=f"{guild.name} ({guild.id})",
        )
        if not await self.bot.disambiguator.confirm(interaction, embed=confirm_embed):
            return

        await guild.leave()
        embed = discord.Embed(
            color=const.Color.prpl,
            description=f"Just left guild {guild.name} with id `{guild.id}`\n",
        )
        await interaction.followup.send(embed=embed)

    @guild_group.command(name="stats")
    async def guild_stats(
        self, interaction: AluInteraction, guild: app_commands.Transform[discord.Guild, DiscordGuildTransformer]
    ) -> None:
        """🚓 Show basic stats about the guild."""
        embed = discord.Embed(color=const.Palette.blue(shade=500), title="Guild Stats")
        embed = self.get_guild_stats(embed, guild)
        await interaction.response.send_message(embed=embed)

    @guild_group.command(name="list")
    async def list(self, interaction: AluInteraction) -> None:
        """🚓 Show list of guilds the bot is in."""
        guild_list = chr(10).join([f"• {item.name} `{item.id}`" for item in self.bot.guilds])
        embed = discord.Embed(
            color=const.Color.prpl,
            description=(f"The bot is in these guilds\n{guild_list}"),
        )
        # TODO: this will break when too many guilds;
        await interaction.response.send_message(embed=embed)

    # @commands.is_owner()
    # @commands.command(hidden=True)
    # async def export_database(self, ctx: Context, db_name: str):
    #     """Export database table with `db_name` to a `.csv` file."""
    #     query = f"COPY (SELECT * FROM {db_name}) TO '/.logs/{db_name}.csv' WITH CSV DELIMITER ',' HEADER;"
    #     await ctx.pool.execute(query)
    #     await ctx.reply('Done')


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(DiscordManagement(bot))
