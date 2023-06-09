from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands
from typing_extensions import Self

if TYPE_CHECKING:
    from .bases import AluGuildContext


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
    async def convert(cls, _ctx: AluGuildContext, argument: str) -> Self:
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
    async def convert(cls, ctx: AluGuildContext, argument: str) -> int:
        try:
            return int(argument)
        except ValueError:
            param = ctx.current_parameter
            if param:
                raise commands.BadArgument(f'{param.name} argument expected a Discord ID not {argument!r}')
            raise commands.BadArgument(f'expected a Discord ID not {argument!r}')
