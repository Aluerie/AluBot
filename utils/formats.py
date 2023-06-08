"""
Helping functions to create better/easier or just human-friendly formatting for various things.
"""

from __future__ import annotations

import datetime
import difflib
import traceback
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Sequence, Union

from dateutil.relativedelta import relativedelta
from discord.ext import commands
from discord.utils import format_dt

if TYPE_CHECKING:
    pass


class Plural:
    """
    Helper class to format tricky Plural nouns

    Examples: ::

        >>> format(Plural(1), 'child|children')  # '1 child'
        >>> format(Plural(8), 'week|weeks')  # '8 weeks'
        >>> f'{Plural(3):reminder}' # 3 reminders
    """

    # licensed MPL v2 from Rapptz/RoboDanny
    # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/formats.py

    def __init__(self, value: int):
        self.value: int = value

    def __format__(self, format_spec: str) -> str:
        v = self.value
        singular, sep, plural = format_spec.partition('|')
        plural = plural or f'{singular}s'
        if abs(v) != 1:
            return f'{v} {plural}'
        return f'{v} {singular}'


def human_join(seq: Sequence[str], delim: str = ', ', final: str = 'or') -> str:
    """
    Join sequence of string in human-like format.

    Example Usage: ::

        >>> human_join(['Conan Doyle', 'Nabokov', 'Fitzgerald'], final='and')
        >>> 'Conan Doyle, Nabokov and Fitzgerald'
    """

    # licensed MPL v2 from Rapptz/RoboDanny
    # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/formats.py

    size = len(seq)
    if size == 0:
        return ''

    if size == 1:
        return seq[0]

    if size == 2:
        return f'{seq[0]} {final} {seq[1]}'

    return delim.join(seq[:-1]) + f' {final} {seq[-1]}'


def human_timedelta(
    dt: Union[datetime.datetime, datetime.timedelta, int, float],
    *,
    source: Optional[datetime.datetime] = None,
    accuracy: Optional[int] = 3,
    brief: bool = False,
    strip: bool = False,
    suffix: bool = True,
) -> str:
    """
    Human timedelta between `dt` and `source` `datetime.datetime`'s.

    Example Usage: ::

        >>> d = datetime.datetime.today().replace(hour=0, minute=0, second=0)
        >>> human_timedelta(d)  # '14 hours, 25 minutes and 15 seconds ago'
        >>> human_timedelta(d, brief=True)  # '14h 39m 48s ago'
        >>> human_timedelta(d, strip=True)  # '14h50m22s ago'
        >>> human_timedelta(20000.5324234, strip=True, suffix=False)  # 5h33m20s

    Parameters
    ----------
    dt : datetime.datetime
        if it is int/float/timedelta then it's assumed to be in the past (as in "dt: int = 5" -> 5 seconds ago)
    source : Optional[datetime.datetime]
        Assumed as now if not given
    accuracy : Optional[int]
        How many unit of time words to return
    brief : bool
        if to abbreviate units of time as one letters such as 'seconds' -> 's'
        if `strip` is True then brief param is ignored.
    strip: bool
        if to strip the return time string from spaces like '22m33s ago'.
    suffix : bool
        If to include 'ago' into return string for past times

    Returns
    -------
    str
        Human readable string describing difference between `dt` and `source`
    """

    # licensed MPL v2 from Rapptz/RoboDanny
    # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/time.py

    if strip:
        brief = True

    now = source or datetime.datetime.now(datetime.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    now = now.replace(microsecond=0)

    match dt:
        case datetime.datetime():
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            dt = dt.replace(microsecond=0)
        case datetime.timedelta():
            dt = now - dt
            dt = dt.replace(microsecond=0)
        case int() | float():
            dt = now - datetime.timedelta(seconds=dt)
        case _:
            raise TypeError(
                'Parameter `dt` must be either of types: `datetime.datetime`, `datetime.timedelta`, `int` or `float`'
            )

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
        output_suffix = ''
    else:
        delta = relativedelta(now, dt)
        output_suffix = ' ago' if suffix else ''

    attrs = [
        ('year', 'y'),
        ('month', 'mo'),
        ('day', 'd'),
        ('hour', 'h'),
        ('minute', 'm'),
        ('second', 's'),
    ]

    output = []
    for attr, brief_attr in attrs:
        elem = getattr(delta, attr + 's')
        if not elem:
            continue

        if attr == 'day':
            weeks = delta.weeks
            if weeks:
                elem -= weeks * 7
                if not brief:
                    output.append(format(Plural(weeks), 'week'))
                else:
                    output.append(f'{weeks}w')

        if elem <= 0:
            continue

        if brief:
            output.append(f'{elem}{brief_attr}')
        else:
            output.append(format(Plural(elem), attr))

    if accuracy is not None:
        output = output[:accuracy]

    if len(output) == 0:
        return 'now'
    else:
        if not brief:
            return human_join(output, final='and') + output_suffix
        else:
            sep = '' if strip else ' '
            return sep.join(output) + output_suffix


def format_dt_tdR(dt: datetime.datetime) -> str:
    """
    Shortcut to combine t, d, R styles together.
    Discord will show something like this:

    "22:57 17/05/2015 5 Years Ago"
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return f"{format_dt(dt, 't')} {format_dt(dt, 'd')} ({format_dt(dt, 'R')})"


def ordinal(n: Union[int, str]) -> str:
    """Convert an integer into its ordinal representation, i.e. 0->'0th', '3'->'3rd'"""
    # Remember that there is always funny lambda possibility
    # ```py
    # ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])
    # print([ordinal(n) for n in range(1,32)])
    # ```
    n = int(n)
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix


def inline_diff(a, b):  # a = old_string, b = new_string
    matcher = difflib.SequenceMatcher(None, a, b)

    def process_tag(tag, i1, i2, j1, j2):
        if tag == 'replace':
            return '~~' + matcher.a[i1:i2] + ' ~~ __' + matcher.b[j1:j2] + '__'  # type: ignore
        if tag == 'delete':
            return '~~' + matcher.a[i1:i2] + '~~'  # type: ignore
        if tag == 'equal':
            return matcher.a[i1:i2]  # type: ignore
        if tag == 'insert':
            return '__' + matcher.b[j1:j2] + '__'  # type: ignore
        assert False, "Unknown tag %r" % tag

    return ''.join(process_tag(*t) for t in matcher.get_opcodes())


# https://stackoverflow.com/questions/39001097/match-changes-by-words-not-by-characters
def inline_word_by_word_diff(a, b):  # a = old_string, b = new_string #
    a, b = a.split(), b.split()
    matcher = difflib.SequenceMatcher(None, a, b)

    def process_tag(tag, i1, i2, j1, j2):
        a_str, b_str = ' '.join(matcher.a[i1:i2]), ' '.join(matcher.b[j1:j2])  # type: ignore
        match tag:
            case 'replace':
                return f'~~{a_str}~~ __{b_str}__'
            case 'delete':
                return f'~~{a_str}~~'
            case 'equal':
                return a_str
            case 'insert':
                return f'__{b_str}__'
        assert False, "Unknown tag %r" % tag

    return ' '.join(process_tag(*t) for t in matcher.get_opcodes())


def block_function(string, blocked_words, whitelist_words):
    for blocked_word in blocked_words:
        if blocked_word.lower() in string.lower():
            for whitelist_word in whitelist_words:
                if whitelist_word.lower() in string.lower():
                    return 0  # allow
            return 1  # block
    return 0  # allow


def indent(symbol, counter, offset, split_size):
    return str(symbol).ljust(len(str(((counter - offset) // split_size + 1) * split_size)), " ")


#######################################################################
# ANSI ################################################################
#######################################################################
# It is not used anywhere in the bot
# because mobile does not support coloured codeblocks/ansi tech
# but well, let's keep it
# https://gist.github.com/kkrypt0nn/a02506f3712ff2d1c8ca7c9e0aed7c06


class AnsiFG(Enum):
    """Ansi foreground colours"""

    gray = 30
    red = 31
    green = 32
    yellow = 33
    blue = 34
    pink = 35
    cyan = 36
    white = 37

    def __int__(self) -> int:
        return self.value


class AnsiBG(Enum):
    """Ansi background colours"""

    firefly_dark_blue = 40
    orange = 41
    marble_blue = 42
    greyish_turquoise = 43
    gray = 44
    indigo = 45
    light_gray = 46
    white = 47

    def __int__(self) -> int:
        return self.value


class AnsiFMT(Enum):
    """Ansi text formats"""

    normal = 0
    bold = 1
    underline = 4

    def __int__(self) -> int:
        return self.value


def ansi(
    text: str,
    *,
    foreground: Optional[AnsiFG] = None,
    background: Optional[AnsiBG] = None,
    bold: bool = False,
    underline: bool = False,
) -> str:
    """Something ansi function"""
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
    final_format = ';'.join(list(map(str, array_join)))
    return f'\u001b[{final_format}m{text}\u001b[0m'


def prepare_exception_for_send(exc: Exception) -> List[str]:
    """

    Returns
    --------
    List[str]
        List of paginated strings ready to be sent to discord
        according to its character limits via webhook or message.
    """
    traceback_content = "".join(traceback.format_exception(exc))

    paginator = commands.Paginator(prefix='```py')
    for line in traceback_content.split('\n'):
        paginator.add_line(line)

    return paginator.pages
