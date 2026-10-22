"""Helpers.

Some utilities that I could not categorize anywhere really.
"""

from __future__ import annotations

import logging

import discord

from . import const, errors, fmt

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def error_handler_response_embed(error: Exception, desc: str, *, unexpected: bool) -> discord.Embed:
    """A boilerplate responses for all cases that happen in error handlers.

    This function uses all "error handler variables" to provide the response.
    """
    if unexpected:
        # means error is unexpected so let's return our ready to go answer
        embed = (
            discord
            .Embed(
                color=const.Color.error,
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
    else:
        # error was expected and has expected `desc` answer template
        embed = discord.Embed(color=const.Color.error, description=desc)
        if not isinstance(error, errors.ErroneousUsage):
            embed.set_author(name=fmt.convert_PascalCase_to_spaces(error.__class__.__name__))

    return embed
