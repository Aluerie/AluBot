"""Interactions.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import contextlib
from typing import TYPE_CHECKING, override

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


async def respond(interaction: Interaction, response: str) -> None:
    with contextlib.suppress(discord.NotFound):
        if not interaction.response.is_done():
            await interaction.response.send_message(response, ephemeral=True)
        else:
            await interaction.followup.send(response, ephemeral=True)


def _build_interaction_error_embed(interaction: Interaction) -> discord.Embed:
    embed = (
        discord
        .Embed(
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
    fmt.add_mapping_field(embed, "Namespace `__dict__`", mapping=interaction.namespace.__dict__)
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
            # "user_perms": interaction.permissions.value,
            # "bot_perms": interaction.app_permissions.value,
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
                await respond(interaction, f"Please retry in {original.retry_after:.1f} sec")
            case app_commands.CommandSignatureMismatch():
                await respond(
                    interaction,
                    "This command's signature is out of date!\n"
                    "I've warned Irene about this and it will be fixed as soon as possible.",
                )
                await interaction.client.notify_developers(str(original))
            case app_commands.CommandNotFound():
                await respond(
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
                    respond=lambda msg: respond(interaction, response=msg),
                ):
                    return

                embed = _build_interaction_error_embed(interaction)
                embed.color = 0x2C0703
                embed.title = f"/{interaction.command.qualified_name}" if interaction.command else "non-cmd interaction"
                await interaction.client.error_notification_manager.register(original, embed)


class UiMixin(ui.view.BaseView):
    """UI Mixin."""

    if TYPE_CHECKING:
        message: discord.Message | discord.WebhookMessage  # or doesn't exist

    @override
    async def on_timeout(self) -> None:
        """On timeout we disable items in view so they are not clickable any longer if possible.

        Requires us to assign message object to view so it can edit the message.
        """
        if hasattr(self, "message"):
            for item in self.children:
                # item in self.children is Select/Button which have ``.disable`` but type-hinted as Item
                item.disabled = True  # ty: ignore[unresolved-attribute]
            await self.message.edit(view=self)

    @override
    async def on_error(
        self, interaction: Interaction, error: Exception, item: discord.ui.Item[discord.ui.View]
    ) -> None:
        if not await interaction.client.respond_per_policy(
            error, respond=lambda msg: respond(interaction, response=msg)
        ):
            return

        embed = _build_interaction_error_embed(interaction)
        embed.color = 0x2A0553
        embed.title = f"View Error: `{self.__class__.__name__}`"
        embed.add_field(name="View Item", value=repr(item))
        await interaction.client.error_notification_manager.register(error, embed)
