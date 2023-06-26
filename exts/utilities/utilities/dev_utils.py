from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, Tuple

import discord
from discord.ext import commands

from utils import AluCog, AluContext
from utils.const import Colour

if TYPE_CHECKING:
    pass


class DevUtilities(AluCog):
    @commands.command()
    async def charinfo(self, ctx: AluContext, *, characters: str):
        """Shows information about character(-s).

        Only up to a 10 characters at a time though.
        """

        def to_string(c: str) -> Tuple[str, str]:
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, None)
            name = f'\\N{{{name}}}' if name else 'Name not found.'
            field_value = f'[`\\U{digit:>08}`](https://www.fileformat.info/info/unicode/char/{digit}) `{c}` {c}'
            return name, field_value

        names: list[str] = []
        e = discord.Embed(colour=discord.Colour.blurple())
        for c in characters[:10]:
            name, field_value = to_string(c)
            e.add_field(name=f'\N{BLACK CIRCLE} `{name}`', value=field_value, inline=False)
            names.append(name)
        if len(characters) > 10:
            e.colour = Colour.error()
            e.set_footer(text='Output was too long. Displaying only first 10 chars.')
        content = "```js\n" + ''.join(names) + "```"  # js codeblock highlights {TEXT HERE} in teal :D 
        await ctx.send(content=content, embed=e)
