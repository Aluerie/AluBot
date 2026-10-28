"""Interactions.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""
# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Views."""

import contextlib
import functools
from typing import Any, override

import discord
from discord import ui

from shared import fmt

from .interactions import Interaction, _build_interaction_error_embed, _respond
from .tree import Interaction, _build_interaction_error_embed, _respond

__all__ = (
    "LayoutView",
    "Modal",
    "UiMixin",
    "View",
)


class UiMixin(ui.view.BaseView):
    """Some boilerplate features for views.

    List it before `ui.View` or `ui.Modal` in the bases.
    """

    message: discord.Message | discord.WebhookMessage | None = None

    @override
    async def on_timeout(self) -> None:
        """Disable the items on timeout. Requires `message` to be assigned so the view can edit it."""
        if self.message is None:
            return

        for child in self.walk_children():
            if isinstance(child, (ui.Select, ui.UserSelect, ui.RoleSelect, ui.ChannelSelect, ui.MentionableSelect)) or (
                isinstance(child, ui.Button) and child.url is None
            ):
                child.disabled = True
        with contextlib.suppress(discord.NotFound, discord.HTTPException):
            await self.message.edit(view=self)

    @override
    async def on_error(
        self,
        interaction: Interaction,
        error: Exception,
        item: discord.ui.Item[Any] | None = None,  # `None` for modals: `Modal.on_error` has no item
        /,
    ) -> None:
        """Event: called when a view item's callback or a modal's submit raises an exception."""
        if not await interaction.client.respond_per_policy(error, respond=functools.partial(_respond, interaction)):
            return

        kind = "Modal" if isinstance(self, ui.Modal) else "View"
        embed = _build_interaction_error_embed(
            interaction,
            title=f"{kind} Error: `{type(self).__name__}`",
            color=0x2A0553,
        )
        fmt.add_mapping_field(embed, name="Interaction Data", mapping=dict(interaction.data or {}))
        if item is not None:
            fmt.add_mapping_field(embed, name="View Item", mapping={"item": item})
        await interaction.client.error_notification_manager.register(error, embed)


class Modal(UiMixin, ui.Modal):
    """Modal."""


class View(UiMixin, ui.View):
    """View."""


class LayoutView(UiMixin, ui.LayoutView):
    """LayoutView."""
