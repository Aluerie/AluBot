from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Union

import re
import difflib
import datetime

from datetime import timedelta

if TYPE_CHECKING:
    pass


def gettimefromhms(strtime):
    def regextime(letter):
        pattern = '\d+(?={})'.format(letter)
        hours = re.search(pattern, strtime)
        if hours:
            hours = int(hours.group(0))
        else:
            hours = 0
        return hours

    ftr = [3600, 60, 1]
    letters = ['h', 'm', 's']
    return sum([a * regextime(b) for a, b in zip(ftr, letters)])


def s(data) -> Literal["", "s"]:
    if isinstance(data, str):
        data = int(not data.endswith("s"))
    elif hasattr(data, "__len__"):
        data = len(data)
    check = data != 1
    return "s" if check else ""


def humanize_time(time: timedelta, full=True) -> str:
    def n(value, key):
        names_dict = {
            'y': {True: f' year', False: 'y'},
            'd': {True: f' day', False: 'd'},
            'h': {True: f' hour', False: 'h'},
            'm': {True: f' minute', False: 'm'},
            's': {True: f' second', False: 's'}
        }
        res = names_dict[key][full]
        if full:
            res += s(value)
        return f"{value}{res}"

    if time.days > 365:
        years, days = divmod(time.days, 365)
        return f"{n(years, 'y')} {n(days, 'd')}"
    if time.days > 1:
        return f"{n(time.days, 'd')} {humanize_time(timedelta(seconds=time.seconds))}"
    hours, seconds = divmod(time.seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours > 0:
        return n(hours, 'h') + ' ' + n(minutes, 'm')
    if minutes > 0:
        return n(minutes, 'm') + ' ' + n(seconds, 's')
    return n(seconds, 's')


def display_hmstime(seconds, granularity=3):
    intervals = (('w', 604800), ('d', 86400), ('h', 3600), ('m', 60), ('s', 1),)
    result = []

    seconds = int(seconds)
    for name, count in intervals:
        value = int(seconds // count)
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{:02}{}".format(value, name))
    answer = ''.join(result[:granularity])
    return answer


def display_relativehmstime(seconds, granularity=3):
    if seconds <= 0:
        return 'just now'
    else:
        return f'{display_hmstime(seconds, granularity=3)} ago'


def display_time(seconds, granularity=5):
    intervals = (('w', 604800), ('d', 86400), ('h', 3600), ('min', 60), ('sec', 1),)
    result = []

    seconds = int(seconds)
    for name, count in intervals:
        value = int(seconds // count)
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append(f"{value} {name}")
    answer = ' '.join(result[:granularity])
    return answer


def ordinal(n: Union[int, str]) -> str:
    """
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    """
    n = int(n)
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    return str(n) + suffix


def inline_diff(a, b):  # a = old_string, b = new_string
    matcher = difflib.SequenceMatcher(None, a, b)

    def process_tag(tag, i1, i2, j1, j2):
        if tag == 'replace':
            return '~~' + matcher.a[i1:i2] + ' ~~ __' + matcher.b[j1:j2] + '__'
        if tag == 'delete':
            return '~~' + matcher.a[i1:i2] + '~~'
        if tag == 'equal':
            return matcher.a[i1:i2]
        if tag == 'insert':
            return '__' + matcher.b[j1:j2] + '__'
        assert False, "Unknown tag %r" % tag
    return ''.join(process_tag(*t) for t in matcher.get_opcodes())


# https://stackoverflow.com/questions/39001097/match-changes-by-words-not-by-characters
def inline_wordbyword_diff(a, b):  # a = old_string, b = new_string #
    a, b = a.split(), b.split()
    matcher = difflib.SequenceMatcher(None, a, b)

    def process_tag(tag, i1, i2, j1, j2):
        a_str, b_str = ' '.join(matcher.a[i1:i2]), ' '.join(matcher.b[j1:j2])
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

# moscow_timezone = timezone('Europe/Moscow')
# before.created_at.astimezone(moscow_timezone).strftime('%H:%M, %d/%m')

def next_weekday(weekday, hour=23, minute=0):
    """
    this function was mainly made for tasks to get a date
    @param weekday:
    @param hour:
    @param minute:
    @return: Next weekday at hour minute from now
    """
    d = datetime.datetime.today().replace(hour=hour, minute=minute)
    print(d)
    days_ahead = weekday - d.weekday()
    return d + datetime.timedelta(days_ahead)


def block_function(string, blocked_words, whitelist_words):
    for blocked_word in blocked_words:
        if blocked_word.lower() in string.lower():
            for whitelist_word in whitelist_words:
                if whitelist_word.lower() in string.lower():
                    return 0  # allow
            return 1  # block
    return 0  # allow


def indent(symbol, counter, offset, split_size):
    return str(symbol).ljust(len(str(((counter-offset)//split_size + 1) * split_size)), " ")
