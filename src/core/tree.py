"""Application Tree.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from typing import TYPE_CHECKING, override

import discord
from discord import app_commands

if TYPE_CHECKING:
    from .bot import AluBot

__all__ = (
    "AppCommandTree",
    "Interaction",
)

type Interaction = discord.Interaction[AluBot]


class AppCommandTree(app_commands.CommandTree):
    """Custom AppCommand Tree class for the AluBot.

    Provides error handler for application commands.
    """

    @override
    async def on_error(
        self,
        interaction: Interaction,
        error: app_commands.AppCommandError,
    ) -> None:  # ty: ignore[invalid-method-override]
        """Event: called when any application command error raises an exception."""
        if isinstance(error, app_commands.CommandInvokeError):
            error: Exception = error.original

        async def respond(response: str) -> None:
            if not interaction.response.is_done():
                await interaction.response.send_message(response)
            else:
                await interaction.followup.send(response)

        match error:
            case app_commands.CommandOnCooldown():
                await respond(f"Please retry in {error.retry_after}")
            case _:
                if not await interaction.client._respond_per_policy(error, respond=respond):
                    return

        # OUTDATED

        if isinstance(error, app_commands.CommandOnCooldown):
            desc = f"Please retry in `{fmt.human_timedelta(error.retry_after, mode='full')}`"
        elif isinstance(error, app_commands.CommandSignatureMismatch):
            desc = (
                "\N{WARNING SIGN} This command's signature is out of date!\n"
                "I've warned the developers about this and it will be fixed as soon as possible."
            )
            warn_developers_desc = (
                f"The signature for command {error.command!r} is different from the one provided by Discord. "
                "This can happen because either your code is out of date or you have not synced the "
                "commands with Discord, causing the mismatch in data. It is recommended to sync the "
                "command tree (globally and guild-bound) to fix this issue."
            )

        elif isinstance(error, app_commands.CommandNotFound):
            desc = (
                "Sorry! \N{WARNING SIGN} Somehow this slash command does not exist anymore.\n"
                "I've warned the developers about this. "
                "Soon the command will either be brought back or deleted from the command list."
            )
            warn_developers_desc = (
                f"Application command {error.name!r} was not found! "
                "Please, resync your app tree (globally and guild-bound). Or check your code."
                f"Command details: \nparents: {error.parents!r}\ntype: {error.type!r}"
            )
        else:
            unexpected = True

            cmd_name = f"/{interaction.command.qualified_name}" if interaction.command else "non-cmd interaction"

            args_join = (
                "\n".join(f"[{name}]: {value!r}" for name, value in interaction.namespace.__dict__.items())
                if interaction.namespace.__dict__
                else "No arguments"
            )
            description = (
                await self.find_mention(interaction.command) or cmd_name
                if isinstance(interaction.command, app_commands.Command)
                else cmd_name
            )
            if interaction.namespace.__dict__:
                description += " " + " ".join(f"{name}: {value}" for name, value in interaction.namespace.__dict__.items())

            snowflake_ids = (
                f"author  = {interaction.user.id}\n"  # comment to prevent formatting from concatenating the lines
                f"channel = {interaction.channel_id}\n"  # so I can see the alignment better
                f"guild   = {interaction.guild_id}"
            )

            metadata_embed = (
                discord
                .Embed(
                    color=0x2C0703,
                    title=f"App Command Error: `{cmd_name}`",
                    description=description,
                    timestamp=interaction.created_at,
                )
                .set_author(
                    name=(
                        f"@{interaction.user} in #{interaction.channel} "
                        f"({interaction.guild.name if interaction.guild else 'DM Channel'})"
                    ),
                    icon_url=interaction.user.display_avatar,
                )
                .add_field(name="Command Arguments", value=fmt.codeblock(args_join, "ps"), inline=False)
                .add_field(name="Snowflake IDs", value=fmt.codeblock(snowflake_ids, "ebnf"), inline=False)
                .set_footer(
                    text=f"on_app_command_error: {cmd_name}",
                    icon_url=interaction.guild.icon if interaction.guild else interaction.user.display_avatar,
                )
            )
            await interaction.client.error_notification_manager.register(error, metadata_embed)
            if interaction.channel_id == interaction.client.hideout.spam_channel_id:
                # we don't need any extra embeds;
                if not interaction.response.is_done():
                    await interaction.response.send_message(":(", ephemeral=True)
                return

        if warn_developers_desc:
            warn_developers_embed = discord.Embed(
                color=const.Color.error,
                description=warn_developers_desc,
            ).set_author(name=error.__class__.__name__)
            await interaction.client.hideout.spam.send(const.Role.error.mention, embed=warn_developers_embed)

        response_embed = helpers.error_handler_response_embed(error, desc, unexpected=unexpected)
