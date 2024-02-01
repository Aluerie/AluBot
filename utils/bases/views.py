from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord

from .. import const
from . import errors

if TYPE_CHECKING:
    from bot import AluBot


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
    ):
        super().__init__(timeout=timeout)
        self.author_id: int | None = author_id

        # we could try doing __class__.__name__ stuff and add spaces, replace "view" with "interactive element"
        # but it might get tricky since like FPCSetupMiscView exists
        self.view_name: str = view_name

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

    async def on_timeout(self) -> None:
        """On timeout we disable items in view so they are not clickable any longer if possible.

        Requires us to assign message object to view so it can edit the message.
        """

        if hasattr(self, "message"):
            for item in self.children:
                # item in self.children is Select/Button which have ``.disable`` but typehinted as Item
                item.disabled = True  # type: ignore
            await self.message.edit(view=self)

    async def on_error(self, interaction: discord.Interaction[AluBot], error: Exception, item: discord.ui.Item[Any]):
        """My own Error Handler for Views"""

        if isinstance(error, errors.AluBotException):
            desc = str(error)

        else:
            # error is unexpected
            desc = "Sorry! something went wrong..."

            extra = f"```py\n[view]: {item.view}\n[item]: {item}\n```"
            await interaction.client.exc_manager.register_error(
                error, interaction, where=f"{item.view.__class__.__name__} error", extra=extra
            )

        response_embed = discord.Embed(colour=const.Colour.maroon, description=desc)
        if not isinstance(error, errors.ErroneousUsage):
            response_embed.set_author(name=error.__class__.__name__)

        if interaction.response.is_done():
            await interaction.followup.send(embed=response_embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=response_embed, ephemeral=True)


class Url(discord.ui.View):
    """Lazy class to make URL button in one line instead of two."""

    def __init__(self, url: str, label: str = "Open", emoji: str | None = None):
        super().__init__()
        self.add_item(discord.ui.Button(label=label, emoji=emoji, url=url))
