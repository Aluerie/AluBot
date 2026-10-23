"""Application Tree.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import contextlib
from typing import TYPE_CHECKING, override

import discord
from discord import app_commands

from shared import clock, fmt

if TYPE_CHECKING:
    from .bot import Bot

__all__ = (
    "AppCommandTree",
    "Interaction",
)

type Interaction = discord.Interaction[Bot]


def _build_interaction_error_embed(interaction: Interaction) -> discord.Embed:
    """Build the error report embed for an application command interaction."""
    embed = (
        discord
        .Embed(
            color=0x2C0703,
            title=f"/{interaction.command.qualified_name}" if interaction.command else "non-cmd interaction",
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
    fmt.add_mapping_field(embed, "Namespace `__dict__`", interaction.namespace.__dict__)
    fmt.add_mapping_field(
        embed,
        "Snowflake IDs",
        {"author": interaction.user.id, "channel": interaction.channel_id, "guild": interaction.guild_id},
    )
    fmt.add_mapping_field(
        embed,
        "Interaction State",
        {
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

        async def respond(response: str) -> None:
            with contextlib.suppress(discord.NotFound):
                if not interaction.response.is_done():
                    await interaction.response.send_message(response, ephemeral=True)
                else:
                    await interaction.followup.send(response, ephemeral=True)

        match original:
            case app_commands.CommandOnCooldown():
                await respond(f"Please retry in {original.retry_after:.1f} sec")
            case app_commands.CommandSignatureMismatch():
                await respond(
                    "This command's signature is out of date!\n"
                    "I've warned Irene about this and it will be fixed as soon as possible."
                )
                await interaction.client.notify_developers(str(original))
            case app_commands.CommandNotFound():
                await respond(
                    "This slash command could not be found. "
                    "I've warned Irene about this and it will be fixed as soon as possible."
                )
                await interaction.client.notify_developers(
                    f"Application command {original.name!r} was not found! "
                    "Please, resync your app tree (globally and guild-bound)."
                )
            case _:
                if not await interaction.client.respond_per_policy(original, respond=respond):
                    return
                embed = _build_interaction_error_embed(interaction)
                await interaction.client.error_notification_manager.register(original, embed)
