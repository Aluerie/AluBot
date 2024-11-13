from __future__ import annotations

import unicodedata

import discord
from discord.ext import commands

from bot import AluCog, AluContext
from utils import const


class DevUtilities(AluCog):
    """Utility functions that are mostly usable to developers like me."""

    @commands.hybrid_command(aliases=["char"])
    async def charinfo(self, ctx: AluContext, *, characters: str) -> None:
        """Shows information about character(-s).

        Only up to a 10 characters at a time though.

        Parameters
        ----------
        characters
            Input up to 10 characters to get format info about.

        """

        def to_string(c: str) -> str:
            digit = f"{ord(c):x}"
            name = unicodedata.name(c, None)
            python_name = f"\\N{{{name}}}" if name else "Name not found."
            u_name = f"[`\\U{digit:>08}`](https://www.fileformat.info/info/unicode/char/{digit})"
            return f"{u_name}: `{python_name}` \N{EM DASH} `{c}` {c}"

        names: list[str] = [to_string(c) for c in characters[:10]]
        if len(characters) > 10:
            names.append("Output was too long. Displaying only first 10 chars.")
        await ctx.send(content="\n".join(names))
