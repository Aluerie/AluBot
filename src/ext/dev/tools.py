"""Tools.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, ClassVar

import discord
from discord import app_commands
from discord.ext import commands

from core import DevCog
from shared import fmt
from utils import const

if TYPE_CHECKING:
    from core import Bot, Context, Interaction


class ToolsCog(DevCog):
    """Tools Cog.

    These commands aren't public only because I don't think people would find them useful.
    It's just some helping commands that I use myself when coding the bot.
    """

    @commands.command(name="invite-link")
    async def invite_link(self, ctx: Context) -> None:
        """Get invite link for the bot.

        Somewhat pointless since 'Add App' button exists.
        But it's useful to have for @YenBot where I removed that button.
        """
        await ctx.send(self.bot.invite_link)

    tools_group = app_commands.Group(
        name="tools-dev",
        description="Useful developer tools.",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    # fmt: off
    KNOWN_CHAR_ABBREVIATIONS: ClassVar[dict[str, str]] = {
        "\u0000": "NUL", "\u0009": "TAB", "\u000a": "LF", "\u000d": "CR", "\u00a0": "NBSP", "\u00ad": "SHY",
        "\u200b": "ZWSP", "\u200c": "ZWNJ", "\u200d": "ZWJ", "\u200e": "LRM", "\u200f": "RLM", "\u202a": "LRE",
        "\u202b": "RLE", "\u202c": "PDF", "\u202d": "LRO", "\u202e": "RLO", "\u2060": "WJ", "\u2066": "LRI",
        "\u2067": "RLI", "\u2068": "FSI", "\u2069": "PDI", "\ufe0e": "VS15", "\ufe0f": "VS16", "\ufeff": "BOM",
    }
    # fmt: on

    def char_info_worker(self, char: str) -> tuple[str, str]:
        r"""Return the Python escape for a character and some info.

        Example
        -------
        "🦢" -> ("\N{SWAN}", "[`\U0001f9a2`](<fileformat link>): SWAN — 🦢")
        """
        codepoint = ord(char)
        alias = self.KNOWN_CHAR_ABBREVIATIONS.get(char)
        name = unicodedata.name(char, "")
        if alias is not None:
            full_name = f"{name} ({alias})" if name else alias
            escape = f"\\N{{{alias}}}"
        elif name:
            full_name = name
            escape = f"\\N{{{name}}}"
        else:
            full_name = "(No name found)"
            escape = f"\\U{codepoint:08x}"

        markdown_link = f"[`\\U{codepoint:08x}`](https://www.fileformat.info/info/unicode/char/{codepoint:x})"
        text_view = discord.utils.escape_markdown(char)
        return escape, f"{markdown_link}: {full_name} \N{EM DASH} {text_view}"

    @tools_group.command()
    async def charinfo(self, interaction: Interaction, characters: app_commands.Range[str, 1, 10]) -> None:
        """🔤 Show Unicode information about character(-s).

        Only up to 10 characters (Unicode code points) at a time though.

        Parameters
        ----------
        characters
            Input up to 10 characters to get format info about.
        """
        escapes, lines = zip(*(self.char_info_worker(c) for c in characters), strict=True)
        echo = discord.utils.escape_markdown(characters)
        codeblock = fmt.codeblock("\n".join(f"'{e}'" for e in escapes))
        bullet_list = "\n".join(f"* {line}" for line in lines)
        await interaction.response.send_message(
            content=f"{echo}\n{codeblock}\n{bullet_list}",
            allowed_mentions=discord.AllowedMentions.none(),
            suppress_embeds=True,
        )


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(ToolsCog(bot))
