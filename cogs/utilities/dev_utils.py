from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, Tuple

import discord
from discord.ext import commands

from utils import AluCog, AluContext
from utils.var import Clr


if TYPE_CHECKING:
    pass


class DevUtilities(AluCog):
    @commands.command()
    async def charinfo(self, ctx: AluContext, *, characters: str):
        """Shows information about a character(-s). \
        Only up to a few characters tho.
        """

        def to_string(c: str) -> Tuple[str, str]:
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, None)
            name = f'\N{BLACK CIRCLE} `\\N{{{name}}}`' if name else 'Name not found.'
            string = f'[`\\U{digit:>08}`](https://www.fileformat.info/info/unicode/char/{digit}) `{c}` {c}'
            return name, string

        e = discord.Embed(colour=discord.Colour.blurple())
        for c in characters[:10]:
            n, s = to_string(c)
            e.add_field(name=n, value=s, inline=False)
        if len(characters) > 10:
            e.colour = Clr.error
            e.set_footer(text='Output was too long. Displaying only first 10 chars.')

        await ctx.send(embed=e)
