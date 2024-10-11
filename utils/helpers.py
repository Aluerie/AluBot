"""Helpers.

Some utilities that I could not categorize anywhere really.
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import TYPE_CHECKING, Any, Self

import discord

from . import const, errors, formats

__all__ = ("measure_time",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class measure_time:  # noqa: N801 # it's fine to call classes lowercase if they aren't used as actual classes per PEP-8.
    """Measure performance time of a contexted codeblock.

    Example:
    -------
    ```py
    with measure_time("My long operation"):
        time.sleep(5)

    async with measure_time("My long async operation"):
        await asyncio.sleep(5)
    ```
    It will output the perf_counter with `log.debug`.

    """

    if TYPE_CHECKING:
        start: float

    def __init__(self, name: str, *, logger: logging.Logger = log) -> None:
        self.name: str = name
        self.log: logging.Logger = logger

    def __enter__(self) -> Self:
        self.start = perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        # PT for Performance Time, maybe there are better ideas for abbreviations.
        self.log.debug("%s PT: %.3f secs", self.name, perf_counter() - self.start)

    # same as ^^^
    async def __aenter__(self) -> Self:
        self.start = perf_counter()
        return self

    async def __aexit__(self, *_: Any) -> None:
        # PT for Performance Time, maybe there are better ideas for abbreviations.
        self.log.debug("%s PT: %.3f secs", self.name, perf_counter() - self.start)


def error_handler_response_embed(error: Exception, is_unexpected: bool, desc: str, mention: bool) -> discord.Embed:
    """A boilerplate responses for all cases that happen in error handlers.

    This function uses all "error handler variables" to provide the response.
    """
    if not mention:
        # means I'm developing and sitting right in the channel
        return discord.Embed(colour=const.Colour.maroon).set_author(name=error.__class__.__name__)
    elif is_unexpected:
        # means error is unexpected so let's return our ready to go answer
        return (
            discord.Embed(
                colour=const.Colour.maroon,
                description=(
                    "Sorry! Something went wrong! I've notified my developer about the error "
                    "with all the details. Hopefully, we'll get it fixed soon.\n"
                    f"Sorry for the inconvenience! {const.Emote.DankL} {const.Emote.DankL} {const.Emote.DankL}"
                ),
            )
            .set_thumbnail(url=const.Picture.DankFix)
            .set_author(name="Oups... Unexpected error!")
            .set_footer(text="PS. No private data was recorded.")
        )
    else:
        # error was expected and has expected `desc` answer template
        embed = discord.Embed(colour=const.Colour.maroon, description=desc)
        if not isinstance(error, errors.ErroneousUsage):
            embed.set_author(name=formats.convert_PascalCase_to_spaces(error.__class__.__name__))
        return embed
