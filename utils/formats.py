"""Helping functions to create better/easier or just human-friendly formatting for various things."""

from __future__ import annotations

import datetime
import difflib
import re
from enum import IntEnum
from itertools import starmap
from typing import TYPE_CHECKING, Any, Literal, override

from dateutil.relativedelta import relativedelta

# remember that we can now use `from utils import formats` into `formats.format_dt` with this:
# which is a bit more convenient.
from discord.utils import TimestampStyle, format_dt

from . import const

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


__all__ = ("plural",)


class plural:  # noqa: N801 # pep8 allows lowercase names for classes that are used as functions
    """Helper class to format tricky plural nouns.

    Examples
    --------
    >>> format(plural(1), "child|children")  # "1 child"
    >>> format(plural(8), "week|weeks")  # "8 weeks"
    >>> f"{plural(3):reminder}" # "3 reminders"

    Sources
    -------
    * Rapptz/RoboDanny (license MPL v2), `plural` class:
        https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/formats.py
    """

    def __init__(self, value: int) -> None:
        self.value: int = value

    @override
    def __format__(self, format_spec: str) -> str:
        v = self.value
        singular, _separator, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"
        if abs(v) != 1:
            return f"{v} {plural}"
        return f"{v} {singular}"


def human_join(seq: Sequence[str], delim: str = ", ", final: str = "or") -> str:
    """Join sequence of string in human-readable format.

    Examples
    --------
    >>> human_join(['Conan Doyle', 'Nabokov', 'Fitzgerald'], final='and')
    'Conan Doyle, Nabokov and Fitzgerald'

    Sources
    -------
    * Rapptz/RoboDanny (license MPL v2)
        https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/formats.py
    """
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return delim.join(seq[:-1]) + f" {final} {seq[-1]}"


def human_timedelta(
    dt: datetime.datetime | datetime.timedelta | float,
    *,
    source: datetime.datetime | None = None,
    accuracy: int | None = 3,
    mode: Literal["full", "brief", "strip"] = "full",
    suffix: bool = True,
) -> str:
    """Human timedelta between `dt` and `source` `datetime.datetime`'s.

    Examples
    --------
    >>> d = datetime.datetime.today().replace(hour=0, minute=0, second=0)
    >>> human_timedelta(d)  # '14 hours, 25 minutes and 15 seconds ago'
    >>> human_timedelta(d, brief=True)  # '14h 39m 48s ago'
    >>> human_timedelta(d, strip=True)  # '14h50m22s ago'
    >>> human_timedelta(20000.5324234, strip=True, suffix=False)  # 5h33m20s

    Parameters
    ----------
    dt
        if it is int/float/timedelta then it's assumed to be in the past (as in "dt: int = 5" -> 5 seconds ago)
    source
        Assumed as now if not given
    accuracy
        How many unit of time words to return
    brief
        if to abbreviate units of time as one letters such as 'seconds' -> 's'
        if `strip` is True then brief param is ignored.
    strip
        if to strip the return time string from spaces like '22m33s ago'.
    suffix
        If to include 'ago' into return string for past times

    Returns
    -------
    str
        Human readable string describing difference between `dt` and `source`

    """
    # licensed MPL v2 from Rapptz/RoboDanny
    # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/time.py

    now = source.astimezone(datetime.UTC) if source else datetime.datetime.now(datetime.UTC)

    match dt:
        # todo: i dont like this garbage
        case datetime.datetime():
            dt = dt.astimezone(datetime.UTC)
        case datetime.timedelta():
            dt = now - dt
        case int() | float():
            dt = now - datetime.timedelta(seconds=dt)

    now = now.replace(microsecond=0)
    dt = dt.replace(microsecond=0)

    # This implementation uses `relativedelta` instead of the much more obvious
    # `divmod` approach with seconds because the seconds approach is not entirely
    # accurate once you go over 1 week in terms of accuracy since you have to
    # hardcode a month as 30 or 31 days.
    # A query like "11 months" can be interpreted as "11 months and 6 days"
    # ---------------------------------------------------------------------
    # if you ever need probably (?)slightly faster and more obvious `divmod` implementation,
    # then `?tag format timedelta` in dpy guild
    if dt > now:
        delta = relativedelta(dt, now)
        output_suffix = ""
    else:
        delta = relativedelta(now, dt)
        output_suffix = " ago" if suffix else ""

    attrs = [
        ("year", "y"),
        ("month", "mo"),
        ("day", "d"),
        ("hour", "h"),
        ("minute", "m"),
        ("second", "s"),
    ]

    output = []
    for attr, brief_attr in attrs:
        elem = getattr(delta, attr + "s")
        if not elem:
            continue

        if attr == "day":
            weeks = delta.weeks
            if weeks:
                elem -= weeks * 7
                if mode == "full":
                    output.append(format(plural(weeks), "week"))
                else:
                    output.append(f"{weeks}w")

        if elem <= 0:
            continue

        if mode == "full":
            output.append(format(plural(elem), attr))
        else:
            output.append(f"{elem}{brief_attr}")

    if accuracy is not None:
        output = output[:accuracy]

    if len(output) == 0:
        return "now"
    if mode == "full":
        return human_join(output, final="and") + output_suffix
    sep = "" if mode == "strip" else " "
    return sep.join(output) + output_suffix


def format_dt_custom(dt: datetime.datetime, *style_letters: TimestampStyle) -> str:
    """Format `datetime.datetime` to discord's application friendly timestamp.

    The Styles Example table:
    (it's copied from discord.py docs - click on TimestampStyle for the original).

    +-------------+----------------------------+-----------------+
    |    Style    |       Example Output       |   Description   |
    +=============+============================+=================+
    | t           | 22:57                      | Short Time      |
    +-------------+----------------------------+-----------------+
    | T           | 22:57:58                   | Long Time       |
    +-------------+----------------------------+-----------------+
    | d           | 17/05/2016                 | Short Date      |
    +-------------+----------------------------+-----------------+
    | D           | 17 May 2016                | Long Date       |
    +-------------+----------------------------+-----------------+
    | f (default) | 17 May 2016 22:57          | Short Date Time |
    +-------------+----------------------------+-----------------+
    | F           | Tuesday, 17 May 2016 22:57 | Long Date Time  |
    +-------------+----------------------------+-----------------+
    | R           | 5 years ago                | Relative Time   |
    +-------------+----------------------------+-----------------+.
    """
    return " ".join([format_dt(dt, letter) for letter in style_letters])


def format_dt_tdR(dt: datetime.datetime) -> str:  # noqa: N802 # tdR is discord format choices.
    """Shortcut to combine t, d, R styles for the discord timestamp together.

    The most used discord timestamp combination in the bot.
    Discord will show something like this:
    "22:57 17/05/2015 5 Years Ago"
    """
    return format_dt_custom(dt, "t", "d", "R")


def ordinal(n: int | str) -> str:
    """Convert an integer into its ordinal representation, i.e. 0->'0th', '3'->'3rd'."""
    n = int(n)
    suffix = "th" if 11 <= n % 100 <= 13 else ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    return str(n) + suffix


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


#######################################################################
# ANSI ################################################################
#######################################################################
# It is not used anywhere in the bot
# because mobile does not support coloured codeblocks/ansi tech
# but well, let's keep it
# https://gist.github.com/kkrypt0nn/a02506f3712ff2d1c8ca7c9e0aed7c06


class AnsiFG(IntEnum):
    """Ansi foreground colours."""

    gray = 30
    red = 31
    green = 32
    yellow = 33
    blue = 34
    pink = 35
    cyan = 36
    white = 37


class AnsiBG(IntEnum):
    """Ansi background colours."""

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
    """Something ansi function."""
    # TODO: make better docs
    # todo: what s the point of ansi function if mobile does not support it
    # todo: check ansi gist for more
    # todo: check if stuff from docs in MyColourFormatting in bot.py works.
    # i think discord ansi is a bit halved
    array_join = [AnsiFMT.normal.value]
    if bold:
        array_join.append(AnsiFMT.bold.value)
    if underline:
        array_join.append(AnsiFMT.underline.value)
    if background:
        array_join.append(background.value)
    if foreground:
        array_join.append(foreground.value)
    final_format = ";".join(list(map(str, array_join)))
    return f"\u001b[{final_format}m{text}\u001b[0m"


def tick(opt: bool | None, /) -> str:  # noqa: FBT001 # this function has just one argument;
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
        """regex_time('h') = 3, regex_time('m') = 51, regex_time('s') = 8 for above example."""
        pattern = rf"\d+(?={letter})"  # UP032
        units = re.search(pattern, hms_time)
        return int(units.group(0)) if units else 0

    timeunit_dict = {"h": 3600, "m": 60, "s": 1}
    return sum(v * letter_to_seconds(letter) for letter, v in timeunit_dict.items())


def divmod_timedelta(total_seconds: float) -> str:
    """Easier human timedelta than `formats.human_timedelta`.

    But because of this, for accuracy sake, this only supports days, hours, minutes, seconds.
    """
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    timeunit_dict = {"d": days, "h": hours, "m": minutes, "s": seconds}
    return "".join(f"{letter}{number}" for letter, number in timeunit_dict.items() if number)


def convert_PascalCase_to_spaces(text: str) -> str:  # noqa: N802 # sorry, I always forget what case is what.
    """Separate PascalCase string with spaces.

    Examples
    --------
    * "CommandNotFound" -> "Command Not Found".

    Source
    ------
    * https://stackoverflow.com/a/9283563/19217368

    """
    return re.sub(r"((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))", r" \1", text)


def convert_camel_case_to_PascalCase(text: str) -> str:  # noqa: N802 # sorry, I always forget what case is what.
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


LiteralAligns = Literal["^", "<", ">"]


class TabularData:
    """A helper class to simplify making a table-like text inside discord codeblocks."""

    def __init__(self, *, outer: str, inner: str, separators: bool) -> None:
        self.outer: str = outer
        self.inner: str = inner
        self.separators: bool = separators

        self._widths: list[int] = []
        self._columns: list[str] = []
        self._aligns: list[LiteralAligns] = []
        self._rows: list[list[str]] = []

    def set_columns(self, columns: list[str], *, aligns: list[LiteralAligns] = []) -> None:
        if aligns and len(aligns) != len(columns):
            msg = "columns and formats parameters should be the same length lists."
            raise ValueError(msg)

        self._columns = columns
        self._aligns = aligns or ["^"] * len(columns)  # fancy default
        self._widths = [len(c) + 2 * len(self.outer) for c in columns]

    def add_row(self, row: Iterable[Any]) -> None:
        rows = [str(r) for r in row]
        self._rows.append(rows)
        for index, element in enumerate(rows):
            width = len(element) + 2 * len(self.outer)
            self._widths[index] = max(width, self._widths[index])

    def add_rows(self, rows: Iterable[Iterable[Any]]) -> None:
        for row in rows:
            self.add_row(row)

    def render(self) -> str:
        """Renders a table."""
        # todo: maybe make render abstract method and impl it in subclasses instead
        # so we don't have this gibberish unclear code with a lot of " if conditions"
        # then remove + 2 * len(self.outer) in self._widths above
        # maybe move set_columns as __init__
        # and add logic where columns is allowed to be empty so like NoBorderTable can be without column names

        def align_properly(e: str, i: int) -> str:
            align_lookup = {"^": e, ">": e + " " * bool(self.outer), "<": " " * bool(self.outer) + e}
            return f"{align_lookup[self._aligns[i]]:{self._aligns[i]}{self._widths[i]}}"

        def get_entry(d: list[str]) -> str:
            elem = f"{self.inner}".join(align_properly(e, i) for i, e in enumerate(d))
            return f"{self.outer}{elem}{self.outer}"

        to_draw = []

        if self.separators:
            sep = "+".join("-" * w for w in self._widths)
            sep = f"+{sep}+"

            to_draw = [sep, get_entry(self._columns), sep]
            to_draw.extend([get_entry(row) for row in self._rows])
            to_draw.append(sep)
        else:
            to_draw = [get_entry(self._columns)]
            to_draw.extend([get_entry(row) for row in self._rows])

        return "\n".join(to_draw)


class RstTable(TabularData):
    """RST Table for Discord Markdown Codeblocks.

    Example:
    -------
    ```txt
    +-------+-----+
    | Name  | Age |
    +-------+-----+
    | Alice | 24  |
    |  Bob  | 19  |
    +-------+-----+
    ```

    """

    def __init__(self) -> None:
        super().__init__(outer="|", inner="|", separators=True)


def code(text: str) -> str:
    """Wrap text into a Python triple "`" discord codeblock.

    It's just annoying to type sometimes. It's also 1 symbol shorter :D
    """
    return f"```py\n{text}```"


class NoBorderTable(TabularData):
    """No line-border Table for Discord Markdown Codeblocks.

    Example:
    -------
    ```txt
    Name  Age
    Alice  24
    Bob    19
    ```

    """

    def __init__(self) -> None:
        super().__init__(outer="", inner=" ", separators=False)


if __name__ == "__main__":
    table = NoBorderTable()
    table.set_columns(["Name", "AgeAgeAgeAgeAge ", "JobTitle"], aligns=["<", ">", "^"])
    table.add_rows([["Alice", 29, "xd"], ["Bob", 23, "artist"]])
    print(table.render())  # noqa: T201
