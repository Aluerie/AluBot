from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands
from discord.ext import commands

from utils import const, errors, formats, helpers

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from .bases import AluInteraction


__all__ = ("AluAppCommandTree",)

log = logging.getLogger(__name__)


class AluAppCommandTree(app_commands.CommandTree):
    """Custom AppCommand Tree class for the AluBot.

    * implements app commands mentions via app_commands store.
    * error handler
    * etc

    Sources
    -------
    * `?tag slashid` in the dpy server
    * gist by @LeoCx1000
        https://gist.github.com/LeoCx1000/021dc52981299b95ea7790416e4f5ca4
    * gist by @Soheab
        https://gist.github.com/Soheab/fed903c25b1aae1f11a8ca8c33243131
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.application_commands: dict[int | None, list[app_commands.AppCommand]] = {}
        """Mapping of `guild_id` (or global scope) to list of App Commands belonging to it."""
        self.cache: dict[
            int | None, dict[app_commands.Command[Any, ..., Any] | commands.HybridCommand[Any, ..., Any] | str, str]
        ] = {}
        """Mapping of `guild_id` (or global scope) to a dictionary containing commands to mentions relation."""

    @override
    async def sync(self, *, guild: discord.abc.Snowflake | None = None) -> list[app_commands.AppCommand]:
        """Method overwritten to store the commands."""
        ret = await super().sync(guild=guild)
        guild_id = guild.id if guild else None
        self.application_commands[guild_id] = ret
        self.cache.pop(guild_id, None)
        return ret

    @override
    async def fetch_commands(self, *, guild: discord.abc.Snowflake | None = None) -> list[app_commands.AppCommand]:
        """Method overwritten to store the commands."""
        ret = await super().fetch_commands(guild=guild)
        guild_id = guild.id if guild else None
        self.application_commands[guild_id] = ret
        self.cache.pop(guild_id, None)
        return ret

    async def get_or_fetch_commands(
        self, *, guild: discord.abc.Snowflake | None = None
    ) -> list[app_commands.AppCommand]:
        """Get the commands from the storage or fetch them from discord."""
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
        """Retrieves the mention of an AppCommand given a specific command name, and optionally, a guild.

        Parameters
        ----------
        command: app_commands.Command[Any, ..., Any] | commands.HybridCommand[Any, ..., Any] | str
            The command to retrieve the mention for.
        guild: discord.abc.Snowflake | None = None
            The scope (guild) from which to retrieve the commands from. If `None` is given or not passed,
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
    ) -> Generator[app_commands.Command[Any, ..., Any], None, None]:
        for command in commands:
            if isinstance(command, app_commands.Group):
                yield from self._walk_children(command.commands)
            else:
                yield command

    async def walk_mentions(
        self, *, guild: discord.abc.Snowflake | None = None
    ) -> AsyncGenerator[tuple[app_commands.Command[Any, ..., Any] | commands.HybridCommand[Any, ..., Any], str], None]:
        """Gets all valid mentions for app commands in a specific guild.

        This takes into consideration group commands, it will only return mentions for
        the command's children, and not the parent as parents aren't mentionable.

        Parameters
        ----------
        guild: discord.Guild | None
            The guild to get commands for. If not given, it will only return global commands.

        Yields
        ------
        tuple[app_commands.Command[Any, ..., Any] | commands.HybridCommand[Any, ..., Any], str]
            The command along with its associated mention.
        """
        for command in self._walk_children(self.get_commands(guild=guild, type=discord.AppCommandType.chat_input)):
            mention = await self.find_mention_for(command, guild=guild)
            if mention:
                yield command, mention
        if guild and self.fallback_to_global is True:
            for command in self._walk_children(self.get_commands(guild=None, type=discord.AppCommandType.chat_input)):
                mention = await self.find_mention_for(command, guild=guild)
                if mention:
                    yield command, mention
                else:
                    log.warning("Could not find a mention for command %s in the API. Are you out of sync?", command)

    @override
    async def on_error(self, interaction: AluInteraction, error: app_commands.AppCommandError | Exception) -> None:
        """Handler called when an error is raised while invoking an app command."""
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original

        # error handler working variables
        desc: str = "No description"
        unexpected: bool = False
        warn_developers_desc: str = ""

        # error handler itself.

        if isinstance(error, commands.BadArgument):  # TODO: remove all those `commands.BadArgument`
            desc = f"{error}"
        elif isinstance(error, errors.AluBotError):
            # These errors are raised in code of this project by myself or with an explanation text as `error`
            desc = f"{error}"
        elif isinstance(error, app_commands.CommandOnCooldown):
            desc = f"Please retry in `{formats.human_timedelta(error.retry_after, mode='full')}`"
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
                await self.find_mention_for(interaction.command) or cmd_name
                if isinstance(interaction.command, app_commands.Command)
                else cmd_name
            )
            if interaction.namespace.__dict__:
                description += " " + " ".join(
                    f"{name}: {value}" for name, value in interaction.namespace.__dict__.items()
                )

            snowflake_ids = (
                f"author  = {interaction.user.id}\n"  # comment to prevent formatting from concatenating the lines
                f"channel = {interaction.channel_id}\n"  # so I can see the alignment better
                f"guild   = {interaction.guild_id}"
            )

            metadata_embed = (
                discord.Embed(
                    colour=0x2C0703,
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
                .add_field(name="Command Arguments", value=formats.code(args_join, "ps"), inline=False)
                .add_field(name="Snowflake IDs", value=formats.code(snowflake_ids, "ebnf"), inline=False)
                .set_footer(
                    text=f"on_app_command_error: {cmd_name}",
                    icon_url=interaction.guild.icon if interaction.guild else interaction.user.display_avatar,
                )
            )
            await interaction.client.exc_manager.register_error(error, metadata_embed, interaction.channel_id)
            if interaction.channel_id == interaction.client.hideout.spam_channel_id:
                # we don't need any extra embeds;
                if not interaction.response.is_done():
                    await interaction.response.send_message(":(")
                return

        if warn_developers_desc:
            warn_developers_embed = discord.Embed(
                colour=const.Colour.error,
                description=warn_developers_desc,
            ).set_author(name=error.__class__.__name__)
            await interaction.client.hideout.spam.send(const.Role.error.mention, embed=warn_developers_embed)

        response_embed = helpers.error_handler_response_embed(error, desc, unexpected=unexpected)
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=response_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=response_embed, ephemeral=True)
