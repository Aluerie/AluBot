from __future__ import annotations

from typing import TYPE_CHECKING, Self, override

import discord
from discord.ext import commands

from utils import AluView, checks, const

from ._base import GuildSettingsCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluGuildContext


class PrefixView(AluView):
    def __init__(
        self,
        *,
        author_id: int | None,
        embed: discord.Embed,
    ) -> None:
        super().__init__(author_id=author_id, view_name="Prefix Setup Message")
        self.embed: discord.Embed = embed

    @discord.ui.button(emoji="\N{HEAVY DOLLAR SIGN}", label="Change prefixes", style=discord.ButtonStyle.gray)
    async def set_prefix(self, interaction: discord.Interaction[AluBot], button: discord.ui.Button[Self]) -> None:
        await interaction.response.send_modal(PrefixModal(self.embed))


class PrefixModal(discord.ui.Modal, title="New Server Prefixes Setup"):
    prefix1 = discord.ui.TextInput(
        style=discord.TextStyle.long,
        label="New primary prefix for the server.",
        placeholder="Enter up to 3 characters...\nLeave empty if you don't need a primary prefix.",
        max_length=3,
        default="",
        required=False,
    )
    prefix2 = discord.ui.TextInput(
        style=discord.TextStyle.long,
        label="New secondary prefix for the server.",
        placeholder="Enter up to 3 characters...\nLeave empty if you don't need a secondary prefix.",
        max_length=3,
        default="",
        required=False,
    )
    prefix3 = discord.ui.TextInput(
        style=discord.TextStyle.long,
        label="New tertiary prefix for the server.",
        placeholder="Enter up to 3 characters...\nLeave empty if you don't need a tertiary prefix.",
        max_length=3,
        default="",
        required=False,
    )

    def __init__(self, embed: discord.Embed) -> None:
        super().__init__()
        self.embed: discord.Embed = embed

    @override
    async def on_submit(self, interaction: discord.Interaction[AluBot]) -> None:
        assert interaction.guild

        input_values = [self.prefix1.value, self.prefix2.value, self.prefix3.value]
        new_prefixes = {p for p in input_values if p}
        query = """
            INSERT INTO guilds (guild_id, prefixes)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
                DO UPDATE SET prefixes = $2
        """
        await interaction.client.pool.execute(query, interaction.guild.id, new_prefixes)

        old_field_name = self.embed.fields[0].name
        if new_prefixes:
            new_field_value = "\n".join(
                f"{counter}. `{prefix}`" for counter, prefix in enumerate(new_prefixes, start=1)
            )
        else:
            new_field_value = "No prefixes currently set."

        self.embed.set_field_at(0, name=old_field_name, value=new_field_value, inline=False)
        await interaction.response.edit_message(embed=self.embed)

        response_embed = discord.Embed(
            colour=discord.Colour.dark_green(),
            description=f"Successfully changed the server prefixes to {', '.join(f'`{p}`' for p in new_prefixes)}.",
        )
        await interaction.followup.send(embed=response_embed)


class PrefixSettings(GuildSettingsCog):
    @checks.hybrid.is_manager()
    @commands.hybrid_command(invoke_without_command=True, aliases=["prefixes"])
    async def prefix(self, ctx: AluGuildContext) -> None:
        """View/Change/Reset prefixes for this server."""
        current_prefixes = self.bot.prefix_cache.get(ctx.guild.id, self.bot.command_prefix)
        embed = (
            discord.Embed(
                colour=const.Colour.blueviolet,
                title="Server Prefix Setup",
                description=(
                    'You can change server prefixes with the button "Change prefixes" below.\n\n'
                    f"The bot also always answers on @-mentions, i.e. {self.bot.user.mention}` help`."
                ),
            )
            .add_field(
                name="Current Prefix(-es) for this Server.",
                value="\n".join(f"{counter}. `{prefix}`" for counter, prefix in enumerate(current_prefixes, start=1)),
                inline=False,
            )
            .set_footer(text=f"PS. The bot's initial historial default prefix is {", ".join(self.bot.command_prefix)}")
        )

        view = PrefixView(author_id=ctx.author.id, embed=embed)
        await ctx.reply(embed=embed, view=view)


async def setup(bot: AluBot) -> None:
    await bot.add_cog(PrefixSettings(bot))
