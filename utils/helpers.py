"""Helpers.

Some utilities that I could not categorize anywhere really.
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import TYPE_CHECKING, Self

import discord

from . import const, errors, formats

__all__ = ("measure_time",)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


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
        end: float

    def __init__(self, name: str, *, logger: logging.Logger = log) -> None:
        self.name: str = name
        self.log: logging.Logger = logger

    def __enter__(self) -> Self:
        self.start = perf_counter()
        return self

    async def __aenter__(self) -> Self:
        self.start = perf_counter()
        return self

    def measure_time(self) -> None:
        """Record and debug-log measured PT (Performance Time).

        Notes
        -----
        * maybe there are better ideas for abbreviations than PT.
        """
        self.end = end = perf_counter() - self.start
        self.log.debug("%s PT: %.3f secs", self.name, end)

    def __exit__(self, *_: object) -> None:
        self.measure_time()

    async def __aexit__(self, *_: object) -> None:
        self.measure_time()


def error_handler_response_embed(error: Exception, desc: str, *, unexpected: bool) -> discord.Embed:
    """A boilerplate responses for all cases that happen in error handlers.

    This function uses all "error handler variables" to provide the response.
    """
    if unexpected:
        # means error is unexpected so let's return our ready to go answer
        return (
            discord.Embed(
                colour=const.Colour.error,
                description=(
                    "Sorry! Something went wrong! I've notified my developer about the error "
                    "with all the details. Hopefully, we'll get it fixed soon.\n"
                    f"Sorry for inconvenience! {const.Emote.DankL} {const.Emote.DankL} {const.Emote.DankL}"
                ),
            )
            .set_thumbnail(url=const.Picture.DankFix)
            .set_author(name="Oups... Unexpected error!")
            .set_footer(text="PS. No private data was recorded.")
        )
    # error was expected and has expected `desc` answer template
    embed = discord.Embed(colour=const.Colour.error, description=desc)
    if not isinstance(error, errors.ErroneousUsage):
        embed.set_author(name=formats.convert_PascalCase_to_spaces(error.__class__.__name__))
    return embed
