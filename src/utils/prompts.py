# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Prompts.

Small reusable "ask the user something" helpers built from views.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Self

import discord
from discord.utils import MISSING

from core import View

if TYPE_CHECKING:
    from core import Interaction

__all__ = (
    "ConfirmView",
    "confirm",
)


class ConfirmView(View):
    """Two buttons: confirm and cancel.

    Attributes
    ----------
    value
        `True` if the author confirmed, `False` if they cancelled and `None` if they did not answer in time.
    """

    def __init__(self, *, author_id: int, timeout: float = 60.0) -> None:
        super().__init__(author_id=author_id, timeout=timeout)
        self.value: bool | None = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Confirm the prompt."""
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Cancel the prompt."""
        self.value = False
        await interaction.response.defer()
        self.stop()


async def confirm(
    interaction: Interaction,
    *,
    embed: discord.Embed | None = None,
    content: str | None = None,
    ephemeral: bool = False,
    timeout: float = 60.0,
) -> bool:
    """Ask the user to confirm something and wait for the answer.

    The prompt message is deleted afterwards.

    Parameters
    ----------
    interaction
        Interaction of the command that needs the confirmation. Only its user can answer the prompt.
    embed
        Embed of the prompt message.
    content
        Text of the prompt message.
    ephemeral
        Whether the prompt message is only visible to the user.
    timeout
        How many seconds the user has to answer.

    Returns
    -------
    bool
        Whether the user confirmed. A cancel and a timeout both give `False`.

    Notes
    -----
    After this function the interaction's initial response is always used up
    (either by the prompt or by the earlier `defer`), so use `interaction.followup` to send the results.
    """
    view = ConfirmView(author_id=interaction.user.id, timeout=timeout)

    # The arguments are spelled out (no `**kwargs`): `Webhook.send` is overloaded and type checkers
    # can't choose an overload when the keywords come from an unpacked dictionary.
    if interaction.response.is_done():
        message = await interaction.followup.send(
            content=content or MISSING,
            embed=embed or MISSING,
            view=view,
            ephemeral=ephemeral,
            wait=True,
        )
    else:
        await interaction.response.send_message(
            content=content or MISSING,
            embed=embed or MISSING,
            view=view,
            ephemeral=ephemeral,
        )
        message = await interaction.original_response()

    await view.wait()

    with contextlib.suppress(discord.HTTPException):
        await message.delete()
    return bool(view.value)
