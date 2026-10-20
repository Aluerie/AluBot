"""Tools.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from core import AluDevCog
from shared import fmt
from utils import const

if TYPE_CHECKING:
    from core import AluBot, AluInteraction


class ToolsCog(AluDevCog):
    """Tools Cog.

    These commands aren't public only because I don't think people would find them useful.
    It's just some helping commands that I use myself when coding the bot.
    """

    tools_group = app_commands.Group(
        name="tools-dev",
        description="🪛 Some useful developer tools .",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @staticmethod
    def needs_escape(char: str) -> bool:
        """Whether a character is a control, separator, or combining mark and should be shown as an escape."""
        return unicodedata.category(char)[0] in "CZM"

    def char_info_worker(self, char: str) -> tuple[str, str]:
        r"""Return the Python escape for a character and a formatted line for the embed.

        Example
        -------
        "🦢" -> ("\N{SWAN}", "[`\U0001f9a2`](<fileformat link>): `\N{SWAN}` — `🦢` 🦢")
        """
        codepoint = ord(char)
        name = unicodedata.name(char, None)
        python_name = f"\\N{{{name}}}" if name is not None else f"\\U{codepoint:08x}"
        embed_name = python_name if name is not None else "(no name)"
        link = f"https://www.fileformat.info/info/unicode/char/{codepoint:x}"
        markdown_link = f"[`\\U{codepoint:08x}`]({link})"

        if self.needs_escape(char):
            escaped = char.encode("unicode_escape").decode()
            code_view = f"`{escaped}`"
            text_view = "\N{SYMBOL FOR SPACE}" if char == " " else escaped
        else:
            code_view = f"`` {char} ``" if char == "`" else f"`{char}`"
            text_view = discord.utils.escape_markdown(char)

        return python_name, f"{markdown_link}: `{embed_name}` \N{EM DASH} {code_view} {text_view}"

    @tools_group.command()
    async def charinfo(self, interaction: AluInteraction, characters: app_commands.Range[str, 1, 10]) -> None:
        """🪛 Show information about character(-s).

        Only up to 10 characters (Unicode code points) at a time though.

        Parameters
        ----------
        characters
            Input up to 10 characters to get format info about.
        """
        names, lines = zip(*(self.char_info_worker(c) for c in characters), strict=True)
        echo = "".join(
            c.encode("unicode_escape").decode() if self.needs_escape(c) else discord.utils.escape_markdown(c)
            for c in characters
        )
        codeblock = fmt.codeblock("\n".join(names))
        await interaction.response.send_message(
            content=f"{echo}\n{codeblock}",
            embed=discord.Embed(
                color=discord.Color.blurple(),
                description="\n".join(lines),
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ToolsCog(bot))
