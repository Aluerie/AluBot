from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from discord.abc import Snowflake

    from .bot import AluBot

    AppCommandStore = dict[str, app_commands.AppCommand]  # {name: app_command}


class AluAppCommandTree(app_commands.CommandTree):
    """Custom Command tree class to set up slash cmds mentions.

    The class makes the tree store app_commands.AppCommand
    to access later for mentioning or anything
    """

    # Credits to @Soheab and their `?tag slashid` in dpy server.
    # https://gist.github.com/Soheab/fed903c25b1aae1f11a8ca8c33243131#file-bot_subclass

    if TYPE_CHECKING:
        on_error: Callable[[discord.Interaction[AluBot], app_commands.AppCommandError], Coroutine[Any, Any, None]]

    def __init__(self, client: AluBot) -> None:
        super().__init__(client=client)
        self._global_app_commands: AppCommandStore = {}
        # guild_id: AppCommandStore
        self._guild_app_commands: dict[int, AppCommandStore] = {}

    def find_app_command_by_names(
        self,
        *qualified_name: str,
        guild: Snowflake | int | None = None,
    ) -> app_commands.AppCommand | None:
        commands_dict = self._global_app_commands
        if guild:
            guild_id = guild.id if not isinstance(guild, int) else guild
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not guild_commands and self.fallback_to_global:
                commands_dict = self._global_app_commands
            else:
                commands_dict = guild_commands

        for cmd_name, cmd in commands_dict.items():
            if any(name in qualified_name for name in cmd_name.split()):
                return cmd

        return None

    def get_app_command(
        self,
        value: str | int,
        guild: Snowflake | int | None = None,
    ) -> app_commands.AppCommand | None:
        def search_dict(d: AppCommandStore) -> app_commands.AppCommand | None:
            for cmd_name, cmd in d.items():
                if value == cmd_name or (str(value).isdigit() and int(value) == cmd.id):
                    return cmd
            return None

        if guild:
            guild_id = guild.id if not isinstance(guild, int) else guild
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not self.fallback_to_global:
                return search_dict(guild_commands)
            else:
                return search_dict(guild_commands) or search_dict(self._global_app_commands)
        else:
            return search_dict(self._global_app_commands)

    @staticmethod
    def _unpack_app_commands(commands: list[app_commands.AppCommand]) -> AppCommandStore:
        ret: AppCommandStore = {}

        def unpack_options(
            options: list[app_commands.AppCommand | app_commands.AppCommandGroup | app_commands.Argument | None],
        ) -> None:
            for option in options:
                if isinstance(option, app_commands.AppCommandGroup):
                    ret[option.qualified_name] = option  # type: ignore
                    unpack_options(option.options)  # type: ignore

        for command in commands:
            ret[command.name] = command
            unpack_options(command.options)  # type: ignore

        return ret

    async def _update_cache(
        self, commands: list[app_commands.AppCommand], guild: Snowflake | int | None = None
    ) -> None:
        # because we support both int and Snowflake
        # we need to convert it to a Snowflake like object if it's an int
        _guild: Snowflake | None = None
        if guild is not None:
            _guild = discord.Object(guild) if isinstance(guild, int) else guild

        if _guild:
            self._guild_app_commands[_guild.id] = self._unpack_app_commands(commands)
        else:
            self._global_app_commands = self._unpack_app_commands(commands)

    @override
    async def fetch_command(self, command_id: int, /, *, guild: Snowflake | None = None) -> app_commands.AppCommand:
        res = await super().fetch_command(command_id, guild=guild)
        await self._update_cache([res], guild=guild)
        return res

    @override
    async def fetch_commands(self, *, guild: Snowflake | None = None) -> list[app_commands.AppCommand]:
        res = await super().fetch_commands(guild=guild)
        await self._update_cache(res, guild=guild)
        return res

    def clear_app_commands_cache(self, *, guild: Snowflake | None) -> None:
        if guild:
            self._guild_app_commands.pop(guild.id, None)
        else:
            self._global_app_commands = {}

    @override
    def clear_commands(
        self,
        *,
        guild: Snowflake | None,
        type: discord.AppCommandType | None = None,
        clear_app_commands_cache: bool = True,
    ) -> None:
        super().clear_commands(guild=guild)
        if clear_app_commands_cache:
            self.clear_app_commands_cache(guild=guild)

    @override
    async def sync(self, *, guild: Snowflake | None = None) -> list[app_commands.AppCommand]:
        res = await super().sync(guild=guild)
        await self._update_cache(res, guild=guild)
        return res
