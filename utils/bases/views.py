"""Custom View subclasses.

This module provides
* AluView class - subclass of discord.ui.View
* AluModal class - subclass of discord.ui.Modal
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord

from .. import const, helpers
from . import errors

if TYPE_CHECKING:
    from bot import AluBot

__all__ = (
    "AluView",
    "AluModal",
)


async def on_views_modals_error(
    view: discord.ui.View,
    interaction: discord.Interaction[AluBot],
    error: Exception,
    item: discord.ui.Item[discord.ui.View] | None = None,
) -> None:
    """Handler called when an error is raised within an AluView or AluModal objects.

    Basically, error handler for views and modals.
    """  # noqa: D401
    error_type: str | None = error.__class__.__name__
    desc: str = "No description"
    unexpected_error: bool = False

    if isinstance(error, errors.ErroneousUsage):
        error_type = None
        desc = f"{error}"
    if isinstance(error, errors.AluBotError):
        desc = str(error)
    else:
        # error is unexpected
        unexpected_error = True

        extra = f"```py\n[view]: {view}"
        if item:
            extra += f"\n[item]: {item}"
        extra += "\n```"
        await interaction.client.exc_manager.register_error(
            error, interaction, where=f"{view.__class__.__name__} error", extra=extra
        )

    response_to_user_embed = helpers.error_handler_response_to_user_embed(unexpected_error, desc, error_type)

    if interaction.response.is_done():
        await interaction.followup.send(embed=response_to_user_embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=response_to_user_embed, ephemeral=True)


class AluView(discord.ui.View):
    """Subclass for discord.ui.View.

    All view elements used in AluBot should subclass this class when using views.
    Because this class provides universal features like error handler.

    Parameters
    ----------
    author_id : int | None
        _description_
    timeout : float | None
        _description_, by default 5*60.0
    view_name : str, optional
        _description_, by default "Interactive Element"

    """

    if TYPE_CHECKING:
        message: discord.Message | discord.InteractionMessage

    def __init__(
        self,
        *,
        author_id: int | None,
        view_name: str = "Interactive Element",
        timeout: float | None = 5 * 60.0,
    ) -> None:
        """Initialize AluView."""
        super().__init__(timeout=timeout)
        self.author_id: int | None = author_id

        # we could try doing __class__.__name__ stuff and add spaces, replace "view" with "interactive element"
        # but it might get tricky since like FPCSetupMiscView exists
        self.view_name: str = view_name

    @override
    async def interaction_check(self, interaction: discord.Interaction[AluBot]) -> bool:
        """Interaction check that blocks non-authors from clicking view items."""
        if self.author_id is None:
            # we allow this view to be controlled by everybody
            return True
        elif interaction.user.id == self.author_id:
            # we allow this view to be controlled only by interaction author
            return True
        else:
            # we need to deny control to this non-author user
            embed = discord.Embed(
                colour=const.Colour.maroon,
                description=f"Sorry! This {self.view_name} is not meant to be controlled by you.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False

    @override
    async def on_timeout(self) -> None:
        """On timeout we disable items in view so they are not clickable any longer if possible.

        Requires us to assign message object to view so it can edit the message.
        """
        if hasattr(self, "message"):
            for item in self.children:
                # item in self.children is Select/Button which have ``.disable`` but typehinted as Item
                item.disabled = True  # type: ignore
            await self.message.edit(view=self)

    @override
    async def on_error(
        self, interaction: discord.Interaction[AluBot], error: Exception, item: discord.ui.Item[discord.ui.View]
    ) -> None:
        """My own Error Handler for Views."""
        await on_views_modals_error(self, interaction, error, item)


class Url(discord.ui.View):
    """Lazy class to make URL button in one line instead of two."""

    def __init__(self, url: str, label: str = "Open", emoji: str | None = None) -> None:
        """Initialize Url object."""
        super().__init__()
        self.add_item(discord.ui.Button(label=label, emoji=emoji, url=url))


class AluModal(discord.ui.Modal):
    """Subclass for discord.ui.Modal.

    Provides an error handler.
    """

    @override
    async def on_error(self, interaction: discord.Interaction[AluBot], error: Exception) -> None:
        await on_views_modals_error(self, interaction, error)
