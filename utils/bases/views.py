from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import discord

if TYPE_CHECKING:
    from utils import AluBot


class AluView(discord.ui.View):
    """
    Subclass for discord.ui.View providing default behaviour for `on_error`
    """

    def __init__(self, *, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)

    async def on_error(self, ntr: discord.Interaction[AluBot], error: Exception, item: discord.ui.Item[Any]):
        await super().on_error(ntr, error, item)

        # TODO: do a better job with embed
        e = discord.Embed(description='Something is wrong with a view.')
        await ntr.client.send_exception(error, embed=e)
        if ntr.response.is_done():
            await ntr.followup.send(f"Sorry! something went wrong....", ephemeral=True)
        else:
            await ntr.response.send_message(f"Sorry! something went wrong....", ephemeral=True)


class Url(discord.ui.View):
    """Lazy class to make URL button in one line instead of two."""

    def __init__(self, url: str, label: str = 'Open', emoji: Optional[str] = None):
        super().__init__()
        self.add_item(discord.ui.Button(label=label, emoji=emoji, url=url))
