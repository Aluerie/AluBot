"""Interactions.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import contextlib
import functools
from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands, ui

from shared import clock, fmt

if TYPE_CHECKING:
    from .bot import Bot

__all__ = (
    "AppCommandTree",
    "Interaction",
    "UiMixin",
)

type Interaction = discord.Interaction[Bot]


async def _respond(interaction: Interaction, response: str) -> None:
    with contextlib.suppress(discord.NotFound):
        if not interaction.response.is_done():
            await interaction.response.send_message(response, ephemeral=True)
        else:
            await interaction.followup.send(response, ephemeral=True)


def _build_interaction_error_embed(interaction: Interaction, *, title: str, color: int) -> discord.Embed:
    """Build the base error report embed for an interaction."""
    embed = (
        discord
        .Embed(
            color=color,
            title=title,
            timestamp=interaction.created_at,
        )
        .set_author(
            name=f"@{interaction.user} in #{interaction.channel}",
            icon_url=interaction.user.display_avatar,
        )
        .set_footer(
            text=interaction.guild.name if interaction.guild else "DM Channel",
            icon_url=interaction.guild.icon if interaction.guild else interaction.user.display_avatar,
        )
    )
    fmt.add_mapping_field(
        embed,
        name="Snowflake IDs",
        mapping={
            "author": interaction.user.id,
            "channel": interaction.channel_id,
            "guild": interaction.guild_id,
        },
    )
    fmt.add_mapping_field(
        embed,
        name="Interaction State",
        mapping={
            "response_done": interaction.response.is_done(),
            "age_seconds": round((clock.utcnow() - interaction.created_at).total_seconds(), 2),
            "locale": interaction.locale.value,
        },
    )
    return embed


class AppCommandTree(app_commands.CommandTree["Bot"]):
    """Custom AppCommand Tree class for the AluBot."""

    @override
    async def on_error(
        self,
        interaction: Interaction,
        error: app_commands.AppCommandError,
        /,
    ) -> None:  # ty: ignore[invalid-method-override]
        """Event: called when any application command error raises an exception."""
        original = error.original if isinstance(error, app_commands.CommandInvokeError) else error

        match original:
            case app_commands.CommandOnCooldown():
                await _respond(interaction, f"Please retry in {original.retry_after:.1f} sec")
            case app_commands.CommandSignatureMismatch():
                await _respond(
                    interaction,
                    "This command's signature is out of date!\n"
                    "I've warned Irene about this and it will be fixed as soon as possible.",
                )
                await interaction.client.notify_developers(str(original))
            case app_commands.CommandNotFound():
                await _respond(
                    interaction,
                    "This slash command could not be found. "
                    "I've warned Irene about this and it will be fixed as soon as possible.",
                )
                await interaction.client.notify_developers(
                    f"Application command {original.name!r} was not found! "
                    "Please, resync your app tree (globally and guild-bound)."
                )
            case _:
                if not await interaction.client.respond_per_policy(
                    original,
                    respond=functools.partial(_respond, interaction),
                ):
                    return

                embed = _build_interaction_error_embed(
                    interaction,
                    title=f"/{interaction.command.qualified_name}" if interaction.command else "non-cmd interaction",
                    color=0x2C0703,
                )
                fmt.add_mapping_field(embed, name="Namespace `__dict__`", mapping=interaction.namespace.__dict__)
                await interaction.client.error_notification_manager.register(original, embed)


_DISABLEABLE = (ui.Button, ui.Select, ui.UserSelect, ui.RoleSelect, ui.ChannelSelect, ui.MentionableSelect)


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
            if isinstance(child, _DISABLEABLE):
                child.disabled = True
        with contextlib.suppress(discord.HTTPException):
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
