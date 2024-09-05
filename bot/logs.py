from __future__ import annotations

import logging
import platform
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, override

import discord

if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = ("setup_logging",)

# generated at https://patorjk.com/software/taag/ using "Standard" font
ASCII_STARTING_UP_ART = r"""
     _    _       ____        _     ____  _             _   _
    / \  | |_   _| __ )  ___ | |_  / ___|| |_ __ _ _ __| |_(_)_ __   __ _
   / _ \ | | | | |  _ \ / _ \| __| \___ \| __/ _` | '__| __| | '_ \ / _` |
  / ___ \| | |_| | |_) | (_) | |_   ___) | || (_| | |  | |_| | | | | (_| |
 /_/   \_\_|\__,_|____/ \___/ \__| |____/ \__\__,_|_|   \__|_|_| |_|\__, |
                                                                    |___/
            [ ALUBOT IS STARTING NOW ]
"""


@contextmanager
def setup_logging(test: bool) -> Generator[Any, Any, Any]:
    """Setup logging."""
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    try:
        # Stream Handler
        handler = logging.StreamHandler()
        handler.setFormatter(get_log_fmt(handler))
        log.addHandler(handler)

        # ensure folder for logs, cfg, temp, etc
        Path(".alubot/").mkdir(parents=True, exist_ok=True)
        # File Handler
        file_handler = RotatingFileHandler(
            filename=f'.alubot/{"alubot" if not test else "yenbot"}.log',
            encoding="utf-8",
            mode="w",
            maxBytes=4 * 1024 * 1024,  # 4 MiB
            backupCount=5,  # Rotate through 5 files
        )
        file_handler.setFormatter(get_log_fmt(file_handler))
        log.addHandler(file_handler)

        if platform.system() == "Linux":
            # so start-ups in logs are way more noticeable
            log.info(ASCII_STARTING_UP_ART)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for h in handlers:
            h.close()
            log.removeHandler(h)


class MyColourFormatter(logging.Formatter):
    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS = (
        (logging.DEBUG, "\x1b[40;1m"),
        (logging.INFO, "\x1b[34;1m"),
        (logging.WARNING, "\x1b[33;1m"),
        (logging.ERROR, "\x1b[31m"),
        (logging.CRITICAL, "\x1b[41m"),
    )

    FORMATS: ClassVar[dict[int, logging.Formatter]] = {
        level: logging.Formatter(
            f"\x1b[37;1m%(asctime)s\x1b[0m | {colour}%(levelname)-7s\x1b[0m | "
            f"\x1b[35m%(name)-30s\x1b[0m | %(lineno)-4d | %(funcName)-30s | %(message)s",
            "%H:%M:%S %d/%m",
        )
        for level, colour in LEVEL_COLOURS
    }

    @override
    def format(self, record: logging.LogRecord) -> str:
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f"\x1b[31m{text}\x1b[0m"

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output


def get_log_fmt(handler: logging.Handler) -> logging.Formatter:
    if (
        isinstance(handler, logging.StreamHandler)
        and discord.utils.stream_supports_colour(handler.stream)
        and not isinstance(handler, RotatingFileHandler)
    ):  # force file handler fmt into `else`
        formatter = MyColourFormatter()
    else:
        formatter = logging.Formatter(
            "{asctime} | {levelname:<7} | {name:<23} | {lineno:<4} | {funcName:<30} | {message}",
            "%H:%M:%S %d/%m",
            style="{",
        )

    return formatter
