from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from utils import const

from ._base import BaseDevCog

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


class Tools(BaseDevCog):
    """Commands and helpful tools that are somewhat useful only to the developers of the bot.

    These commands aren't public only because I don't think people would find them useful.
    It's just some helping commands that I use myself when coding the bot.
    """

    tools_group = app_commands.Group(
        name="tools-dev",
        description="\N{SCREWDRIVER} Some useful tools for AluBot's developers.",
        guild_ids=[const.Guild.hideout, const.Guild.community],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @tools_group.command()
    async def charinfo(self, interaction: AluInteraction, characters: str) -> None:
        """🪛 Shows information about character(-s).

        Only up to a 10 characters at a time though.

        Parameters
        ----------
        characters: str
            Input up to 10 characters to get format info about.

        """

        def to_string(c: str) -> tuple[str, str]:
            """Returns Pythonic Emoji name and a whole string for the slash command's embed.

            Example
            -------
            🦢 -> ("\N{SWAN}", "[\U0001f9a2](*fileformat link*): \N{SWAN} — 🦢 🦢")
            """
            digit = f"{ord(c):x}"
            name = unicodedata.name(c, None)
            python_name = f"\\N{{{name}}}" if name else '"Name not found"'
            u_name = f"[`\\U{digit:>08}`](https://www.fileformat.info/info/unicode/char/{digit})"
            return python_name, f"{u_name}: `{python_name}` \N{EM DASH} `{c}` {c}"

        content_parts = []
        description_parts = []

        for c in characters[:10]:
            python_name, desc_name = to_string(c)
            content_parts.append(python_name)
            description_parts.append(desc_name)

        content = f"{characters}\n```js\n" + "\n".join(content_parts) + "```"
        embed = discord.Embed(color=discord.Color.blurple(), description="\n".join(description_parts))
        if len(characters) > 10:
            embed.set_footer(text="Output was too long. Displaying only first 10 chars.")

        await interaction.response.send_message(content=content, embed=embed)

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
