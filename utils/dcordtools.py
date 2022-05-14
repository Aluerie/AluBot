from discord import abc, Bot, Embed
from discord.ext import commands
from utils.var import Uid, Cid, Clr, umntn

import traceback
from typing import Union


async def send_traceback(
        error: Exception,
        dest: Union[Bot, abc.Messageable],
        *,
        embed: Embed = None,
        mention_dev: bool = True,
        verbosity: int = 10,
):
    if isinstance(dest, Bot):
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
        content = '' if not mention_dev else umntn(Uid.irene)
        await channel.send(content=content, embed=embed)

    message = None
    for page in paginator.pages:
        message = await channel.send(page)
    return message


async def scnf(ctx):
    if ctx.invoked_subcommand is None:
        prefix = getattr(ctx, 'clean_prefix', '/')

        def get_command_signature(command):
            extra_space = '' if command.signature == '' else ' '
            return f'{prefix}{command.qualified_name}{extra_space}{command.signature}'

        embed = Embed(colour=Clr.error)
        embed.set_author(name='SubcommandNotFound')
        ans = 'This command is used only with subcommands. Please, provide one of them:\n'
        ans += '\n'.join([f'`{get_command_signature(c)}`' for c in ctx.command.commands])
        embed.description = ans
        embed.set_footer(text=f'`{prefix}help {ctx.command.name}` for more info')
        return await ctx.respond(embed=embed)


# just convert `keyword: inout_to_10`
def inout_to_10(argument):
    lowered = argument.lower()
    if lowered in ("in", "yes", "y", "true", "t", "1", "enable", "on"):
        return 1
    elif lowered in ("out", "no", "n", "false", "f", "0", "disable", "off"):
        return 0
    else:
        raise commands.errors.BadBoolArgument(lowered)


def ansi(
        string: str,
        colour: str = None,
        background: str = None,
        bold: bool = False,
        underline: bool = False
) -> str:
    """Something something ansi function"""
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
