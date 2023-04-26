from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    pass


class MyColourFormatter(logging.Formatter):
    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS = [
        (logging.DEBUG, '\x1b[40;1m'),
        (logging.INFO, '\x1b[34;1m'),
        (logging.WARNING, '\x1b[33;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]

    FORMATS = {
        level: logging.Formatter(
            f'\x1b[37;1m%(asctime)s\x1b[0m | {colour}%(levelname)-7s\x1b[0m | '
            f'\x1b[35m%(name)-23s\x1b[0m | %(lineno)-4d | %(funcName)-30s | %(message)s',
            '%H:%M:%S %d/%m',
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output


def get_log_fmt(handler: logging.Handler):
    if (
        isinstance(handler, logging.StreamHandler)
        and discord.utils.stream_supports_colour(handler.stream)
        and not isinstance(handler, RotatingFileHandler)
    ):  # force file handler fmt into `else`
        formatter = MyColourFormatter()
    else:
        formatter = logging.Formatter(
            '{asctime} | {levelname:<7} | {name:<23} | {lineno:<4} | {funcName:<30} | {message}',
            '%H:%M:%S %d/%m',
            style='{',
        )

    return formatter
