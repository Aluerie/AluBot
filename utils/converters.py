from __future__ import annotations

import inspect
import re
from typing import TYPE_CHECKING, Any, List, Tuple

import discord
from discord import app_commands
from discord.ext import commands
from PIL import ImageColor
from typing_extensions import Self

from . import const
from .bases import AluBotException

if TYPE_CHECKING:
    from .bases import AluContext


def my_bool(argument: str):
    """My own bool converter

    Same as discord.py `(..., var: bool)` but with "in/out" -> True/False
    Example: $levels opt in/out - to opt in or out of levels system.
    """
    lowered = argument.lower()
    if lowered in ("in", "yes", "y", "true", "t", "1", "enable", "on"):
        return True
    elif lowered in ("out", "no", "n", "false", "f", "0", "disable", "off"):
        return False
    else:
        raise commands.errors.BadBoolArgument(lowered)


class Codeblock:
    """Parsed codeblock from discord message if there is such markdown
    Attributes
    ---------
    language: Optional[str]
        empty '' string if
            - language was not given in ``` codeblock
            - if it is singular ` codeblock
            - if it is not codeblock
    """

    def __init__(self, code: str, language: str = ''):
        self.code: str = code
        self.language: str = language

    @classmethod
    async def convert(cls, _ctx: AluContext, argument: str) -> Self:
        argument = argument.lstrip()  # Even tho it's left-stripped by default in the lib :thinking:

        # if we ever want regex implementation then
        # pattern is ```[^\S\r\n]*[a-z]*(?:\n(?!```$).*)*\n``` for triple backtick

        # current implementation is a bit free but in the end it's "on working" basis meaning
        # it's my duty to deliver code that going to work within agreed logic
        # the code is either ```{lang}\n{code}```, `{code}` or `code`
        # yes we can put some backticks or whitespaces to pass some badly formatted codeblock,
        # > we do not bother with `commands.BadArgument` but instead let SyntaxError be triggered.
        if argument.startswith('```'):  # ```py\nprint('code')```
            backticks = '```'
            split = argument.split('\n', maxsplit=1)
            code = split[1]
            language = split[0].removeprefix(backticks)
        elif argument.startswith('`'):  # `print('code')`
            backticks = '`'
            code = argument[1:]
            language = ''
        else:  # print('code')
            backticks = ''
            code = argument
            language = ''

        code = code.rstrip().removesuffix(backticks).rstrip()
        return cls(code=code, language=language)


# This is because Discord is stupid with Slash Commands and doesn't actually have integer types.
# So to accept snowflake inputs you need a string and then convert it into an integer.
class Snowflake:
    @classmethod
    async def convert(cls, ctx: AluContext, argument: str) -> int:
        try:
            return int(argument)
        except ValueError:
            param = ctx.current_parameter
            if param:
                raise commands.BadArgument(f'{param.name} argument expected a Discord ID not {argument!r}')
            raise commands.BadArgument(f'expected a Discord ID not {argument!r}')


class InvalidColour(AluBotException):
    """Exception for custom cases of AluColourConverter."""

    __slots__: Tuple[str, ...] = ()


class AluColourConverter(commands.ColourConverter):  # , app_commands.Transformer):
    """Some super overloaded colour converted made for /colour command."""

    async def convert(self, ctx: AluContext, argument: str) -> discord.Colour:
        # TODO: we will rename command: for below, probably so be careful.
        error_footer = f'\n\nTo see supported colour formats by the bot - use "{const.Slash.help}` command: colour`"'

        # my custom situations/desires.
        if argument == 'prpl':
            # my fav colour, of course.
            return const.Colour.prpl()

        # Material Palette
        m = re.match(r"mp\(\s*([a-zA-Z]+)\s*,\s*(\d+)\s*\)$", argument)
        if m:
            colour_name = m.group(1)
            shade = int(m.group(2))
            try:
                return getattr(const.MaterialPalette, colour_name)(shade)
            except AttributeError:
                methods = [m[0] for m in inspect.getmembers(const.MaterialPalette, predicate=inspect.ismethod)]
                raise InvalidColour(
                    f'Provided colour name is incorrect.\n\n'
                    'MaterialUI Google Palette supports the following colour names:'
                    f'\n{", ".join(f"`{m}`" for m in methods)}{error_footer}'
                )
            except ValueError:
                raise InvalidColour(
                    'Provided shade value is incorrect.\n\n'
                    'MaterialUI Google Palette supports the following shades values:'
                    f'\n{", ".join(f"`{v}`" for v in const.MaterialPalette.shades)}{error_footer}'
                )

        # Material Accent Palette
        m = re.match(r"map\(\s*([a-zA-Z]+)\s*,\s*(\d+)\s*\)$", argument)
        if m:
            colour_name = m.group(1)
            shade = int(m.group(2))
            try:
                return getattr(const.MaterialAccentPalette, colour_name)(shade)
            except AttributeError:
                methods = [m[0] for m in inspect.getmembers(const.MaterialAccentPalette, predicate=inspect.ismethod)]
                raise InvalidColour(
                    f'Provided colour name is incorrect.\n\n'
                    'MaterialAccentUI Google Palette supports the following colour names:'
                    f'\n{", ".join(f"`{m}`" for m in methods)}{error_footer}'
                )
            except ValueError:
                raise InvalidColour(
                    'Provided shade value is incorrect.\n\n'
                    'MaterialAccentUI Google Palette supports the following shades values:'
                    f'\n{", ".join(f"`{v}`" for v in const.MaterialAccentPalette.shades)}{error_footer}'
                )

        # ImageColor
        try:
            # https://pillow.readthedocs.io/en/stable/reference/ImageColor.html
            rgb: Tuple[int, int, int] = ImageColor.getcolor(argument, "RGB")  # type:ignore
            return discord.Colour.from_rgb(*rgb)
        except ValueError:
            pass

        try:
            return await super().convert(ctx, argument)
        except commands.BadColourArgument:
            raise InvalidColour(f'Colour `{argument}` is invalid.{error_footer}')

    # async def transform(self, interaction: discord.Interaction, value: str):
    #     return await self.convert(interaction, value)  # type: ignore
    # # todo: do it properly (idk how but for now should be fine since super().convert does not use ctx)

    # async def autocomplete(self, _: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    #     colours = ['prpl', 'rgb(', 'hsl(', 'hsv(', 'mp(', 'map('] + list(ImageColor.colormap.keys())
    #     return [
    #         app_commands.Choice(name=Colour, value=Colour) for Colour in colours if current.lower() in Colour.lower()
    #     ][:25]
