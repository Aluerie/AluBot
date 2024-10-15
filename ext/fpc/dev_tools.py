from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands

from utils import const, errors, formats
from utils.dota import NEW_HERO_EMOTE, Hero, HeroTransformer  # TCH001
from utils.lol import NEW_CHAMPION_EMOTE, Champion, ChampionTransformer  # TCH001

from .base_classes import FPCCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils.fpc import Character


class FPCDevTools(FPCCog):
    hideout_devfpc = app_commands.Group(
        name="devfpc",  # cspell: ignore devfpc
        description="Dota 2 FPC (Favourite Player+Character) Hideout-only commands.",
        guild_ids=[const.Guild.hideout],
    )

    hideout_devfpc_dota = app_commands.Group(
        name="dota",
        description="Dota 2 FPC (Favourite Player+Character) Hideout-only commands.",
    )

    hideout_devfpc_lol = app_commands.Group(
        name="lol",
        description="League of Legends FPC (Favourite Player+Character) Hideout-only commands.",
    )

    async def create_emote_helper(
        self,
        interaction: discord.Interaction[AluBot],
        character: Character,
        *,
        default_new_emote: str,
        guild_id: int,
        emote_source_url: str,
        emote_name: str,
    ) -> None:
        await interaction.response.defer()

        if character.emote != default_new_emote:
            msg = f"We already have emote for {character!r}: {character.emote}"
            raise errors.ErroneousUsage(msg)

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            msg = f"Guild id={guild_id} is `None`."
            raise errors.SomethingWentWrong(msg)

        new_emote = await guild.create_custom_emoji(
            name=emote_name,
            image=await self.bot.transposer.url_to_bytes(emote_source_url),
        )

        embed = (
            discord.Embed(
                colour=const.Colour.blueviolet,
                title=f"New emote for {character!r} was created.",
                description=f'```py\n{new_emote.name} = "{new_emote}"```',
            )
            .add_field(
                name=character.display_name,
                value=str(new_emote),
            )
            .set_footer(text="Copy it to your code!")
        )
        await interaction.response.send_message(embed=embed)

    @hideout_devfpc_dota.command(name="emote")
    async def hideout_devfpc_dota_emote(
        self, interaction: discord.Interaction[AluBot], hero: app_commands.Transform[Hero, HeroTransformer]
    ) -> None:
        """Create a new discord emote for a Dota 2 hero.

        Useful when a new Dota 2 hero gets added to the game, so we can just use this command,
        copy-paste the answer to `utils.const` and be happy.
        """
        await self.create_emote_helper(
            interaction,
            hero,
            default_new_emote=NEW_HERO_EMOTE,
            guild_id=const.EmoteGuilds.DOTA[3],
            emote_source_url=hero.minimap_icon_url,
            emote_name=formats.convert_camel_case_to_PascalCase(hero.short_name),
        )

    @hideout_devfpc_lol.command(name="emote")
    async def hideout_devfpc_lol_emote(
        self, interaction: discord.Interaction[AluBot], champion: app_commands.Transform[Champion, ChampionTransformer]
    ) -> None:
        """Create a new discord emote for a League of Legends champion.

        Useful when a new LoL champion gets added to the game, so we can just use this command,
        copy-paste the answer to `utils.const` and be happy.
        """
        await self.create_emote_helper(
            interaction,
            champion,
            default_new_emote=NEW_CHAMPION_EMOTE,
            guild_id=const.EmoteGuilds.LOL[3],
            emote_source_url=champion.icon_url,
            emote_name=champion.alias,
        )


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FPCDevTools(bot))
