"""Views.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord

from utils import const

if TYPE_CHECKING:
    from .tree import Interaction

__all__ = (
    "AluLayoutView",
    "AluModal",
    "AluView",
    "Url",
)


class AluView(discord.ui.View):
    """Subclass for discord.ui.View.

    All view elements used in AluBot should subclass this class when using views.
    Because this class provides universal features like error handler.

    Parameters
    ----------
    author_id: int | None
        Author of the Interactive View . The bot will disallow other people to interact with elements of this View.
        If `None` then everybody is allowed to do so.
    view_name: str, optional
        _description_, by default "Interactive Element"

    """

    if TYPE_CHECKING:
        message: discord.Message | discord.WebhookMessage
        """Note that technically this attribute might not exist because we manually assign it after sending the message.
        Therefore check for `hasattr(self, "message")` when needed.
        """

    def __init_subclass__(cls, name: str = "Interactive Element") -> None:
        cls.name: str = name
        """Essentially a display name for the View, which is shown to the end-user in some cases.

        We can try doing __class__.__name__ stuff and add spaces instead of "Interactive Element",
        but it might get tricky since like FPCSetupMiscView exists
        """
        return super().__init_subclass__()

    def __init__(
        self,
        *,
        author_id: int | None,
        timeout: float | None = 180.0,
    ) -> None:
        """Initialize AluView."""
        super().__init__(timeout=timeout)
        self.author_id: int | None = author_id

    @override
    async def interaction_check(self, interaction: AluInteraction) -> bool:
        """Interaction check that blocks non-authors from clicking view items."""
        if self.author_id is None:
            # we allow this view to be controlled by everybody
            return True
        if interaction.user.id == self.author_id:
            # we allow this view to be controlled only by interaction author
            return True
        # we need to deny control to this non-author user
        embed = discord.Embed(
            color=const.Color.error,
            description=f"Sorry! This `{self.name}` is not meant for you.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False


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
    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await on_views_modals_error(self, interaction, error)


class AluLayoutView(discord.ui.LayoutView):
    """Subclass for discord.ui.View.

    All view elements used in AluBot should subclass this class when using views.
    Because this class provides universal features like error handler.

    Parameters
    ----------
    author_id: int | None
        Author of the Interactive View . The bot will disallow other people to interact with elements of this View.
        If `None` then everybody is allowed to do so.
    view_name: str, optional
        _description_, by default "Interactive Element"

    """

    if TYPE_CHECKING:
        message: discord.Message | discord.WebhookMessage
        """Note that technically this attribute might not exist because we manually assign it after sending the message.
        Therefore check for `hasattr(self, "message")` when needed.
        """

    def __init_subclass__(cls, name: str = "Interactive Element") -> None:
        cls.name: str = name
        """Essentially a display name for the View, which is shown to the end-user in some cases.

        We can try doing __class__.__name__ stuff and add spaces instead of "Interactive Element",
        but it might get tricky since like FPCSetupMiscView exists
        """
        return super().__init_subclass__()

    def __init__(
        self,
        *,
        author_id: int | None,
        timeout: float | None = 180.0,
    ) -> None:
        """Initialize AluView."""
        super().__init__(timeout=timeout)
        self.author_id: int | None = author_id

    @override
    async def interaction_check(self, interaction: Interaction) -> bool:
        """Interaction check that blocks non-authors from clicking view items."""
        if self.author_id is None:
            # we allow this view to be controlled by everybody
            return True
        if interaction.user.id == self.author_id:
            # we allow this view to be controlled only by interaction author
            return True
        # we need to deny control to this non-author user
        embed = discord.Embed(
            color=const.Color.error,
            description=f"Sorry! This `{self.name}` is not meant for you.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
