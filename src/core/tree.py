# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Interactions."""

import contextlib
import functools
import logging
from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands

from shared import clock, fmt

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from discord.ext import commands

    from .bot import Bot

__all__ = (
    "AppCommandTree",
    "Interaction",
)


_log = logging.getLogger(__name__)

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
            # "locale": interaction.locale.value,
        },
    )
    return embed


class AppCommandTree(app_commands.CommandTree["Bot"]):
    """Custom AppCommand Tree class for the AluBot."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.application_commands: dict[int | None, list[app_commands.AppCommand]] = {}
        self.cache: dict[
            int | None, dict[app_commands.Command[Any, ..., Any] | commands.HybridCommand[Any, ..., Any] | str, str]
        ] = {}

    # --- ERROR HANDLER ------------------------------------------------------------------------------------------------

    @override
    async def on_error(
        self,
        interaction: Interaction,
        error: app_commands.AppCommandError,
        /,
    ) -> None:  # ty: ignore[invalid-method-override]
        """Event: called when any application command error raises an exception."""
        match error:
            case app_commands.CommandInvokeError():
                original = error.original
            case app_commands.TransformerError() if isinstance(error.__cause__, Exception):
                # discord.py wraps everything that isn't an `AppCommandError` raised inside a transformer,
                # but we want the error handling to see (and respond to) the original exception
                original = error.__cause__
            case _:
                original = error

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

    # --- MENTIONABLE TREE ---------------------------------------------------------------------------------------------
    # Allows for finding a mention for a given app command
    # Sources
    # -------
    # * '?tag slashid' in the Discord.py server
    # * '?tag mentionable tree' in the  Discord.py server
    # * gist by @LeoCx1000: https://gist.github.com/LeoCx1000/021dc52981299b95ea7790416e4f5ca4
    # * gist by @Soheab: https://gist.github.com/Soheab/fed903c25b1aae1f11a8ca8c33243131

    @override
    async def sync(self, *, guild: discord.abc.Snowflake | None = None) -> list[app_commands.AppCommand]:
        """Sync: method overwritten to store the commands."""
        ret = await super().sync(guild=guild)
        guild_id = guild.id if guild else None
        self.application_commands[guild_id] = ret
        self.cache.pop(guild_id, None)
        return ret

    @override
    async def fetch_commands(self, *, guild: discord.abc.Snowflake | None = None) -> list[app_commands.AppCommand]:
        """Fetch commands: method overwritten to store the commands."""
        ret = await super().fetch_commands(guild=guild)
        guild_id = guild.id if guild else None
        self.application_commands[guild_id] = ret
        self.cache.pop(guild_id, None)
        return ret

    async def get_or_fetch_commands(
        self, *, guild: discord.abc.Snowflake | None = None
    ) -> list[app_commands.AppCommand]:
        """Get or fetch commands: store them."""
        try:
            return self.application_commands[guild.id if guild else None]
        except KeyError:
            return await self.fetch_commands(guild=guild)

    async def find_mention_for(
        self,
        command: app_commands.Command[Any, ..., Any] | commands.HybridCommand[Any, ..., Any] | str,
        *,
        guild: discord.abc.Snowflake | None = None,
    ) -> str | None:
        """Retrieve the mention of an AppCommand given a specific command name, and optionally, a guild.

        Parameters
        ----------
        command
            The command to retrieve the mention for.
        guild
            The scope (guild) from which to retrieve the commands from. If None is given or not passed,
            only the global scope will be searched, however the global scope will also be searched if
            a guild is passed.

        Returns
        -------
        str | None
            The command mention, if found.
        """
        guild_id = guild.id if guild else None
        try:
            return self.cache[guild_id][command]
        except KeyError:
            pass

        # If a guild is given, and fallback to global is set to True, then we must also
        # check the global scope, as commands for both show in a guild.
        check_global = self.fallback_to_global is True and guild is not None

        if isinstance(command, str):
            # Try and find a command by that name. discord.py does not return children from tree.get_command, but
            # using walk_commands and utils.get is a simple way around that.
            command_ = discord.utils.get(self.walk_commands(guild=guild), qualified_name=command)

            if check_global and not command_:
                command_ = discord.utils.get(self.walk_commands(), qualified_name=command)

        else:
            command_ = command

        if not command_:
            return None

        local_commands = await self.get_or_fetch_commands(guild=guild)
        app_command_found = discord.utils.get(local_commands, name=(command_.root_parent or command_).name)

        if check_global and not app_command_found:
            global_commands = await self.get_or_fetch_commands(guild=None)
            app_command_found = discord.utils.get(global_commands, name=(command_.root_parent or command_).name)

        if not app_command_found:
            return None

        mention = f"</{command_.qualified_name}:{app_command_found.id}>"
        self.cache.setdefault(guild_id, {})
        self.cache[guild_id][command] = mention
        return mention

    def _walk_children(
        self, commands: list[app_commands.Group | app_commands.Command[Any, ..., Any]]
    ) -> Generator[app_commands.Command[Any, ..., Any]]:
        for command in commands:
            if isinstance(command, app_commands.Group):
                yield from self._walk_children(command.commands)
            else:
                yield command

    async def walk_mentions(
        self, *, guild: discord.abc.Snowflake | None = None, yield_unknown: bool = False
    ) -> AsyncGenerator[tuple[app_commands.Command[Any, ..., Any] | commands.HybridCommand[Any, ..., Any], str | None]]:
        """Get all valid mentions for app commands in a specific guild.

        This takes into consideration group commands, it will only return mentions for
        the command's children, and not the parent as parents aren't mentionable.

        Parameters
        ----------
        guild
            The guild to get commands for. If not given, it will only return global commands.
        yield_unknown
            If this is set to True, the yielded mention can be None, instead of it being ignored. Defaults to False.

        Yields
        ------
        Tuple[Union[app_commands.Command`, commands.HybridCommand], str]

        """
        for command in self._walk_children(self.get_commands(guild=guild, type=discord.AppCommandType.chat_input)):
            mention = await self.find_mention_for(command, guild=guild)
            if mention is not None or yield_unknown:
                yield command, mention
        if guild and self.fallback_to_global is True:
            for command in self._walk_children(self.get_commands(guild=None, type=discord.AppCommandType.chat_input)):
                mention = await self.find_mention_for(command, guild=guild)
                if mention is not None or yield_unknown:
                    yield command, mention
                else:
                    _log.warning("Could not find a mention for command %s in the API. Are you out of sync?", command)
