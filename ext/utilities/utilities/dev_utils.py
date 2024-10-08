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

        def to_string(c: str) -> tuple[str, str]:
            digit = f"{ord(c):x}"
            name = unicodedata.name(c, None)
            name = f"\\N{{{name}}}" if name else "Name not found."
            field_value = f"[`\\U{digit:>08}`](https://www.fileformat.info/info/unicode/char/{digit}) `{c}` {c}"
            return name, field_value

        names: list[str] = []
        embed = discord.Embed(colour=discord.Colour.blurple())
        for c in characters[:10]:
            name, field_value = to_string(c)
            embed.add_field(name=f"\N{BLACK CIRCLE} `{name}`", value=field_value, inline=False)
            names.append(name)
        if len(characters) > 10:
            embed.colour = const.Colour.maroon
            embed.set_footer(text="Output was too long. Displaying only first 10 chars.")
        content = "```js\n" + "".join(names) + "```"  # js codeblock highlights {TEXT HERE} in teal :D
        await ctx.send(content=content, embed=embed)
