"""Helping functions to create better/easier or just human-friendly formatting for various things."""

from __future__ import annotations

import difflib
import re
from enum import IntEnum
from itertools import starmap
from typing import Literal

import tabulate

# remember that we can now use `from utils import formats` into `formats.format_dt` with this:
# which is a bit more convenient.
from . import const

# https://github.com/astanin/python-tabulate/issues/195#issuecomment-1270483262
tabulate.MIN_PADDING = 0


def inline_diff(a: str, b: str) -> str:
    """Return inline difference between strings `a` and `b`.

    Where a = old_string, b = new_string.
    """
    matcher = difflib.SequenceMatcher(None, a, b)

    def process_tag(tag: Literal["replace", "delete", "equal", "insert"], i1: int, i2: int, j1: int, j2: int) -> str:
        """Process Tags coming from matcher.get_opcodes().

        Dev Notes
        -----
        * Originally, this function (from wherever I copied it) had `matcher.` before each `a` and `b`.
        """
        if tag == "replace":
            return "~~" + a[i1:i2] + " ~~ __" + b[j1:j2] + "__"
        if tag == "delete":
            return "~~" + a[i1:i2] + "~~"
        if tag == "equal":
            return a[i1:i2]
        if tag == "insert":
            return "__" + b[j1:j2] + "__"
        # Unreachable code
        msg = f"Unknown tag {tag!r}"
        raise AssertionError(msg)

    return "".join(starmap(process_tag, matcher.get_opcodes()))


# https://stackoverflow.com/questions/39001097/match-changes-by-words-not-by-characters
def inline_word_by_word_diff(before: str, after: str) -> str:
    """Return Inline word by word difference between two strings.

    This assumes some discord markdown, i.e.
    * cross out words that got deleted
    * italics for words that are new
    * combine both of above for replacements^

    """
    a, b = before.split(), after.split()  # a = old_string, b = new_string
    matcher = difflib.SequenceMatcher(None, a, b)

    def process_tag(tag: Literal["replace", "delete", "equal", "insert"], i1: int, i2: int, j1: int, j2: int) -> str:
        a_str, b_str = " ".join(a[i1:i2]), " ".join(b[j1:j2])
        match tag:
            case "replace":
                return f"~~{a_str}~~ __{b_str}__"
            case "delete":
                return f"~~{a_str}~~"
            case "equal":
                return a_str
            case "insert":
                return f"__{b_str}__"
            case _:
                # Unreachable code
                msg = f"Unknown tag {tag!r}"
                raise AssertionError(msg)

    return " ".join(starmap(process_tag, matcher.get_opcodes()))


def block_function(string: str, blocked_words: list[str], whitelist_words: list[str]) -> bool:
    for blocked_word in blocked_words:
        if blocked_word.lower() in string.lower():
            return all(whitelist_word.lower() not in string.lower() for whitelist_word in whitelist_words)  # block
    return False  # allow


def label_indent(label: str | int, counter: int, split_size: int) -> str:
    """Label indent to properly adjust spaces in fake'ish discord app table.

    It's better to explain with an example.
    When showing a message/embed - discord eats all the spaces in the content, making it much harder to align columns
    in tabulate-like tables without triple backtick ``` codeblocks.
    But for some things, like tables containing Discord emotes - we cannot use codeblocks.

    Therefore we need some small magic to calculate offset spacing ourselves.

    Examples
    --------
    >>> label_indent("81", 81, 20)
    "81 "

    Note the extra space after 81, this is because that page of the table will also contain a number 100.
    so this space makes `81 `, `100` (we surround the numbers with backticks in discord markdown tables)
    to look properly aligned.
    """
    return str(label).ljust(len(str(counter + split_size)), " ")


class AnsiFG(IntEnum):
    """Ansi foreground colors."""

    gray = 30
    red = 31
    green = 32
    yellow = 33
    blue = 34
    pink = 35
    cyan = 36
    white = 37


class AnsiBG(IntEnum):
    """Ansi background colors."""

    firefly_dark_blue = 40
    orange = 41
    marble_blue = 42
    greyish_turquoise = 43
    gray = 44
    indigo = 45
    light_gray = 46
    white = 47


class AnsiFMT(IntEnum):
    """Ansi text formats."""

    normal = 0
    bold = 1
    underline = 4


def ansi(
    text: str,
    *,
    foreground: AnsiFG | None = None,
    background: AnsiBG | None = None,
    bold: bool = False,
    underline: bool = False,
) -> str:
    r"""Format text in ANSI colors for discord.

    Discord doesn't support bright colors in ANSI formats (90-97 and 100-107) or dim text highlight.

    Warning
    -------
    Currently, it's not used anywhere in the bot because the coloring doesn't work on mobile.
    But I've figured out that late so let's keep the code.

    Sources
    -------
    * Gist by kkrypt0nn  # cSpell:words kkrypt
        https://gist.github.com/kkrypt0nn/a02506f3712ff2d1c8ca7c9e0aed7c06

    Examples
    --------
    >>> res = formats.ansi("wow", foreground=formats.AnsiFG.blue, background=formats.AnsiBG.gray, bold=True)
    >>> await self.spam.send(f"```ansi\n{res}```")

    Note, that we need to embed the string(-s) within "```ansi" codeblock.
    """
    array_join = [AnsiFMT.normal.value]
    if bold:
        array_join.append(AnsiFMT.bold.value)
    if underline:
        array_join.append(AnsiFMT.underline.value)
    if background:
        array_join.append(background.value)
    if foreground:
        array_join.append(94)
    final_format = ";".join(list(map(str, array_join)))
    return f"\u001b[{final_format}m{text}\u001b[0m"


def tick(opt: bool | None, /) -> str:  # ruff: ignore[boolean-type-hint-positional-argument] # this function has just one argument;
    lookup = {
        True: const.Tick.Yes,
        False: const.Tick.No,
        None: const.Tick.Black,
    }
    return lookup.get(opt, const.Tick.Question)


def hms_to_seconds(hms_time: str) -> int:
    """Convert time in hms format like "03h51m08s" to seconds.

    Example, `twitchio.Video.duration` have this in a such format so I need to convert it to seconds.
    like this: "03h51m08s" -> 3 * 3600 + 51 * 60 + 8 = 13868
    """

    def letter_to_seconds(letter: str) -> int:
        """letter_to_seconds('h') = 3, letter_to_seconds('m') = 51, letter_to_seconds('s') = 8 for above example."""
        pattern = rf"\d+(?={letter})"  # UP032
        units = re.search(pattern, hms_time)
        return int(units.group(0)) if units else 0

    timeunit_dict = {"h": 3600, "m": 60, "s": 1}
    return sum(v * letter_to_seconds(letter) for letter, v in timeunit_dict.items())


def convert_PascalCase_to_spaces(text: str) -> str:  # ruff: ignore[invalid-function-name] # sorry, I always forget what case is what.
    """Separate PascalCase string with spaces.

    Examples
    --------
    * "CommandNotFound" -> "Command Not Found".

    Source
    ------
    * https://stackoverflow.com/a/9283563/19217368

    """
    return re.sub(r"((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))", r" \1", text)


def convert_camel_case_to_PascalCase(text: str) -> str:  # ruff: ignore[invalid-function-name] # sorry, I always forget what case is what.
    """Convert camel_case string into PascalCase.

    Examples
    --------
    * "snake_case_name" -> "SnakeCaseName".

    Source
    ------
    * https://stackoverflow.com/a/1176023/19217368 (last section of the answer)

    Returns
    -------
    A string converted to PascalCase.
    """
    return "".join(word.title() for word in text.split("_"))


def color_to_str(value: int) -> str:
    """Convert integer colour to a string #RRGGBB representation.

    For som reason, PIL library in some places accepts colours in this string format (but not `int`).
    """
    return f"#{value:0>6x}"
