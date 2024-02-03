"""Helpers

Some utilities that I could not categorize anywhere really.
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import TYPE_CHECKING, Self

import discord

from . import const, formats

if TYPE_CHECKING:
    from types import TracebackType

__all__ = ("measure_time",)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class measure_time:  # noqa: N801 # it's fine to call classes lowercase if they aren't used as actual classes per PEP-8.
    """A helper tool to quickly measure performance time
    of the codeblock we contexting in

    Use it like this:
    ```py
    with measure_time("My long operation"):
        time.sleep(5)
    ```
    It will output the perf_counter with `log.debug`.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self) -> Self:
        self.start = perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        # PT for Performance Time, maybe there are better ideas for abbreviations.
        log.debug("%s PT: %.3f secs", self.name, perf_counter() - self.start)


def unexpected_error_embed() -> discord.Embed:
    """Unexpected error embed.

    This embed is used in error handlers and in base classes such as `on_error` on Views.
    """
    return (
        discord.Embed(
            colour=const.Colour.maroon,
            description=(
                "I've notified my developer about the error and sent all the details. "
                "Hopefully, we'll get it fixed soon.\n"
                f"Sorry for the inconvenience! {const.Emote.DankL} {const.Emote.DankL} {const.Emote.DankL}"
            ),
        )
        .set_thumbnail(url=const.Picture.DankFix)
        .set_author(name="Oups... Unexpected error!")
    )

def error_handler_response_to_user_embed(
        unexpected_error: bool,
        desc: str,
        error_type: str | None
) -> discord.Embed:
    if unexpected_error:
        return unexpected_error_embed()
    else:
        embed = discord.Embed(colour=const.Colour.maroon, description = desc)
        if error_type:
            embed.set_author(name=formats.convert_pascal_case_to_spaces(error_type))
        return embed
