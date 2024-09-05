from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import const, errors, formats, helpers

if TYPE_CHECKING:
    from bot import AluBot


async def on_app_command_error(
    interaction: discord.Interaction[AluBot], error: app_commands.AppCommandError | Exception
) -> None:
    """Handler called when an error is raised while invoking an app command."""
    # Hmm, idk I still want commands to go through this handler if any error occurs
    # not sure how to achieve analogical to "ctx.is_error_handled" behaviour
    # if command is not None:
    #     if command._has_any_error_handlers():
    #         return

    if isinstance(error, app_commands.CommandInvokeError):
        error = error.original

    # error handler working variables
    desc: str = "No description"
    unexpected_error: bool = False
    mention: bool = True

    warn_developers_desc: str = ""

    # error handler itself.

    if isinstance(error, commands.BadArgument):  # TODO: remove all those `commands.BadArgument`
        desc = f"{error}"
    elif isinstance(error, errors.AluBotError):
        # These errors are generally raised in code by myself or by my code with an explanation text as `error`
        # AluBotException subclassed exceptions are all mine.
        desc = f"{error}"
    elif isinstance(error, app_commands.CommandOnCooldown):
        desc = f"Please retry in `{formats.human_timedelta(error.retry_after, mode='full')}`"
    # elif isinstance(error, errors.SilentError):
    #     # this will fail the interaction hmm
    #     cmd = f'/{ntr.command.qualified_name}' if ntr.command else '?-cmd ntr'
    #     logging.debug(f'Ignoring silent command error raised in application command {cmd}', exc_info=False)
    #     return
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
        unexpected_error = True

        cmd_name = f"/{interaction.command.qualified_name}" if interaction.command else "non-cmd interaction"
        metadata_embed = (
            discord.Embed(
                colour=0x2C0703,
                title=f"Error in `{cmd_name}`",
                # timestamp = interaction.created_at
            )
            .add_field(
                name="Command Arguments",
                value=(
                    "```py\n"
                    + "\n".join(f"[{name}]: {value!r}" for name, value in interaction.namespace.__dict__.items())
                    + "```"
                    if interaction.namespace.__dict__
                    else "```py\nNo arguments```"
                ),
            )
            .add_field(
                name="Snowflake Ids",
                value=(
                    "```py\n"
                    f"author  = {interaction.user.id}\n"
                    f"channel = {interaction.channel_id}\n"
                    f"guild   = {interaction.guild_id}```"
                ),
                inline=False,
            )
            .set_author(
                name=(
                    f"@{interaction.user} in #{interaction.channel} "
                    f"({interaction.guild.name if interaction.guild else "DM Channel"})"
                ),
                icon_url=interaction.user.display_avatar,
            )
            .set_footer(
                text=f"on_app_command_error: {cmd_name}",
                icon_url=interaction.guild.icon if interaction.guild else interaction.user.display_avatar,
            )
        )
        mention = interaction.channel_id != interaction.client.hideout.spam_channel_id
        await interaction.client.exc_manager.register_error(error, metadata_embed, mention=mention)

    if warn_developers_desc:
        warn_developers_embed = discord.Embed(
            colour=const.Colour.maroon,
            description=warn_developers_desc,
        ).set_author(name=error.__class__.__name__)
        await interaction.client.hideout.spam.send(const.Role.error_ping.mention, embed=warn_developers_embed)

    response_embed = helpers.error_handler_response_embed(error, unexpected_error, desc, mention)
    if not interaction.response.is_done():
        await interaction.response.send_message(embed=response_embed, ephemeral=True)
    else:
        await interaction.followup.send(embed=response_embed, ephemeral=True)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    bot.old_tree_error = bot.tree.on_error
    bot.tree.on_error = on_app_command_error


async def teardown(bot: AluBot) -> None:
    """Unload AluBot extension. Framework of discord.py."""
    bot.tree.on_error = bot.old_tree_error
