from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from utils import const

from ._base import BaseDevCog

if TYPE_CHECKING:
    from core import AluBot, AluInteraction


class Tools(BaseDevCog):
    """Commands and helpful tools that are somewhat useful only to the developers of the bot.

    These commands aren't public only because I don't think people would find them useful.
    It's just some helping commands that I use myself when coding the bot.
    """

    tools_group = app_commands.Group(
        name="tools-dev",
        description="🪛 Some useful tools for AluBot's developers.",
        guild_ids=[const.Guild.hideout, const.Guild.community],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @tools_group.command()
    async def emote_str(self, interaction: AluInteraction, emote: str) -> None:
        """🪛 Shows emote string in a `<?a:name:id>` format.

        For some reason, without Nitro it's quite annoying to get such strings for animated emotes
        because the backslash trick doesn't work since I can't use the emote myself.

        Parameters
        ----------
        emote: str
            Input an emote or emote's name like "AYAYA".
        """
        if re.findall(const.Regex.EMOTE, emote):
            # `emote` is an actual Discord Emote, it's already in `<?a:name:id>` format
            # could just use "\"-trick in this case :D
            await interaction.response.send_message(content=f"`{emote}`")
        else:
            # `emote` is a string for which we need to find an emote for
            all_emotes = [emoji for guild in interaction.client.guilds for emoji in guild.emojis]
            content = "\n".join(
                f"{emoji} - `{emoji}`" for emoji in filter(lambda e: e.name.lower() == emote.lower(), all_emotes)
            )
            await interaction.response.send_message(content=content)

    @tools_group.command()
    async def yoink_emote(self, interaction: AluInteraction, emote_name: str) -> None:
        """🪛 Yoink emote from this server to the bot's application emojis.

        Parameters
        ----------
        emote_name: str
            Input an emote or emote's name like "AYAYA".
        """
        assert interaction.guild
        existing = discord.utils.find(
            lambda e: e.name.lower() == emote_name.lower() or str(e) == emote_name, interaction.guild.emojis
        )
        if not existing:
            await interaction.response.send_message("This server doesn't have any emotes named like that.")
            return

        created = await self.bot.create_application_emoji(name=existing.name, image=await existing.read())
        await interaction.response.send_message(f"Successfully yoinked {created}.")
        # TODO: make embeds for this? also this is not the best implementation, we need to think of cases where we want
        # to yoink from messages;


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Tools(bot))
