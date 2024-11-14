from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, NamedTuple

import discord
from discord import app_commands

from bot import AluCog

if TYPE_CHECKING:
    from bot import AluBot


class DevUtilities(AluCog):
    """Utility functions that are mostly usable to developers like me."""

    @app_commands.command()
    async def charinfo(self, interaction: discord.Interaction[AluBot], characters: str) -> None:
        """Shows information about character(-s).

        Only up to a 10 characters at a time though.

        Parameters
        ----------
        characters
            Input up to 10 characters to get format info about.

        """

        def to_string(c: str) -> tuple[str, str]:
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

        content = "```js\n" + "\n".join(content_parts) + "```"
        embed = discord.Embed(colour=discord.Colour.blurple(), description="\n".join(description_parts))
        if len(characters) > 10:
            embed.set_footer(text="Output was too long. Displaying only first 10 chars.")

        await interaction.response.send_message(content=content, embed=embed)
