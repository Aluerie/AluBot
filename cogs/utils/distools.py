from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Union, List, Optional

import discord
from discord import Embed, Interaction
from discord.ext import commands

from . import pages
from .context import Context
from .var import Lmt, Cid, umntn, Uid

if TYPE_CHECKING:
    from discord import abc, Colour, Message


async def send_pages_list(
        ctx: Union[Context, Interaction],
        string_list: List[str],
        *,
        split_size: int,
        title: str = None,
        description_prefix: str = '',
        colour: Optional[Union[int, Colour]] = None,
        footer_text: str = None,
        author_name: str = None,
        author_icon: str = None,
) -> Message:
    """helper command to send possibly paginated strings"""
    if split_size != 0:
        places_list = [string_list[x:x + split_size] for x in range(0, len(string_list), split_size)]
    else:
        places_list = [string_list]

    paginator = commands.Paginator(
        prefix='',
        suffix='',
        max_size=Lmt.Embed.description,
    )
    for lines in places_list:
        for line in lines:
            paginator.add_line(line)
        paginator.close_page()

    embeds = [
        Embed(
            colour=colour,
            title=title,
            description=description_prefix + page
        )
        for page in paginator.pages
    ]
    if author_name:
        for em in embeds:
            em.set_author(name=author_name, icon_url=author_icon)
    if footer_text:
        for em in embeds:
            em.set_footer(text=footer_text)

    if len(embeds) == 1:
        if isinstance(ctx, Context):
            return await ctx.reply(embeds=embeds)
        elif isinstance(ctx, Interaction):
            return await ctx.response.send_message(embeds=embeds)
    else:
        pag = pages.Paginator(pages=embeds)
        return await pag.send(ctx)


async def send_traceback(
        error: Exception,
        dest: Union[commands.Bot, discord.Client, abc.Messageable],
        *,
        embed: Embed = None,
        mention_dev: bool = True,
        verbosity: int = 10,
):
    if isinstance(dest, (commands.Bot, discord.Client)):
        channel = dest.get_channel(Cid.spam_me)
    elif isinstance(dest, abc.Messageable):
        channel = dest
    else:
        raise TypeError('Expected Union[Bot, abc.Messageable]')

    etype, value, trace = type(error), error, error.__traceback__
    traceback_content = "".join(
        traceback.format_exception(etype, value, trace, verbosity)
    ).replace("``", "`\u200b`")

    paginator = commands.Paginator(prefix='```python')
    for line in traceback_content.split('\n'):
        paginator.add_line(line)

    if mention_dev or embed:
        content = '' if not mention_dev else umntn(Uid.alu)
        await channel.send(content=content, embed=embed)

    message = None
    for page in paginator.pages:
        message = await channel.send(page)
    return message


# just convert `keyword: inout_to_10`
def inout_to_10(argument):
    lowered = argument.lower()
    if lowered in ("in", "yes", "y", "true", "t", "1", "enable", "on"):
        return 1
    elif lowered in ("out", "no", "n", "false", "f", "0", "disable", "off"):
        return 0
    else:
        raise commands.errors.BadBoolArgument(lowered)


def to_lower(argument):
    return argument.lower()


def ansi(
        string: str,
        colour: str = None,
        background: str = None,
        bold: bool = False,
        underline: bool = False
) -> str:
    """Something ansi function"""
    ansi_dict = {
        'colour': {
            'gray': 30,
            'red': 31,
            'green': 32,
            'yellow': 33,
            'blue': 34,
            'pink': 35,
            'cyan': 36,
            'white': 37
        },
        'background': {
            'firefly dark blue': 40,
            'orange': 41,
            'marble blue': 42,
            'greyish turquoise': 43,
            'gray': 44,
            'indigo': 45,
            'light gray': 46,
            'white': 47
        }
    }
    array_join = [0]
    if bold:
        array_join.append(1)
    if underline:
        array_join.append(4)
    if background := ansi_dict['background'].get(background, None):  # TODO: maybe raise exception there
        array_join.append(background)
    if colour := ansi_dict['colour'].get(colour, None):  # TODO: maybe raise exception there
        array_join.append(colour)
    final_format = ';'.join(list(map(str, array_join)))
    return f'\u001b[{final_format}m{string}\u001b[0m'


class Ansi:
    class Clr:
        gray = 30
        red = 31
        green = 32
        yellow = 33
        blue = 34
        pink = 35
        cyan = 36,
        white = 37

    class Bg:
        firefly_dark_blue = 40
        orange = 41
        marble_blue = 42
        greyish_turquoise = 43
        gray = 44
        indigo = 45
        light_gray = 46
        white = 47

    @classmethod
    def p(
            cls,
            string: str,
            clr: int = None,
            bg: int = None,
            bold: bool = False,
            underline: bool = False
    ) -> str:
        """docs later"""
        array_join = [0]
        if bold:
            array_join.append(1)
        if underline:
            array_join.append(4)
        if bg:
            array_join.append(bg)
        if clr:
            array_join.append(clr)
        final_format = ';'.join(list(map(str, array_join)))
        return f'\u001b[{final_format}m{string}\u001b[0m'
