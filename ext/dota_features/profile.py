from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord
import steam
from discord import app_commands
from tabulate import tabulate

from bot import AluCog
from utils import const, errors

if TYPE_CHECKING:
    from bot import AluBot


class SteamUserTransformer(app_commands.Transformer):
    """Simple steam user converter."""

    @override
    async def transform(self, interaction: discord.Interaction[AluBot], argument: str) -> steam.User:
        try:
            return await interaction.client.dota.fetch_user(steam.utils.parse_id64(argument))
        except steam.InvalidID:
            id64 = await steam.utils.id64_from_url(argument)
            if id64 is None:
                msg = f"Steam User `{argument!r}` not found."
                raise errors.BadArgument(msg) from None
            return await interaction.client.dota.fetch_user(id64)
        except TimeoutError:
            msg = f"Been searching for `{argument!r}` too long - did not found."
            raise errors.TimeoutError(msg) from None

    @override
    async def autocomplete(
        self,
        interaction: discord.Interaction[AluBot],
        arg: str,
    ) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name="Aluerie", value="112636165")]


class SteamDotaProfiles(AluCog):
    @app_commands.command()
    async def steam(
        self,
        interaction: discord.Interaction[AluBot],
        user: app_commands.Transform[steam.User, SteamUserTransformer],
    ) -> None:
        """🔎 Show some basic info on a steam user."""
        await interaction.response.defer()

        embed = (
            discord.Embed(title=user.name)
            .set_thumbnail(url=user.avatar.url)
            .add_field(
                name="Steam IDs",
                value=f'```{tabulate(
                    [
                        ["ID64", str(user.id64)],
                        ["ID32", str(user.id)],
                        ["ID3", str(user.id3)],
                        ["ID2", str(user.id2)],
                    ], tablefmt="plain",
                )}\n```',
                inline=False,
            )
            .add_field(name="Currently playing:", value=f"{user.app or 'Nothing'}")
            # .add_field(name="Friends:", value=len(await user.friends()))
            .add_field(name="Apps:", value=len(await user.apps()))
        )
        await interaction.followup.send(embed=embed)

    @app_commands.guilds(*const.MY_GUILDS)
    @app_commands.command(name="history")
    async def match_history(self, interaction: discord.Interaction[AluBot]) -> None:
        """🔎 Show Aluerie's Dota 2 recent match history."""
        await interaction.response.defer()

        player = interaction.client.dota.aluerie()
        history = await player.match_history()

        embed = discord.Embed(
            description="\n".join(
                [
                    (
                        f"{count}. {match.hero} "
                        f"{(await interaction.client.dota.heroes.by_id(match.hero)).emote} - {match.id}"
                    )
                    for count, match in enumerate(history)
                ],
            ),
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(SteamDotaProfiles(bot))
