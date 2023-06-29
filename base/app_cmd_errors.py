from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from utils import const, errors

if TYPE_CHECKING:
    from utils import AluBot


async def on_app_command_error(ntr: discord.Interaction[AluBot], error: app_commands.AppCommandError | Exception):
    """Handler called when an error is raised while invoking an app command."""

    # Hmm, idk I still want commands to go through this handler if any error occurs
    # not sure how to achieve analogical to "ctx.is_error_handled" behaviour
    # if command is not None:
    #     if command._has_any_error_handlers():
    #         return

    if isinstance(error, app_commands.CommandInvokeError):
        error = error.original

    error_type = error.__class__.__name__

    if isinstance(error, errors.ErroneousUsage):
        # raised by myself but it's not an error per se, thus i dont give error type to the user.
        error_type = None
        desc = f'{error}'
    elif isinstance(error, errors.AluBotException):
        # These errors are generally raised in code by myself or by my code with an explanation text as `error`
        # AluBotException subclassed exceptions are all mine.
        desc = f'{error}'
    elif isinstance(error, app_commands.CommandOnCooldown):
        desc = f"Please retry in `{ntr.client.formats.human_timedelta(error.retry_after, brief=True)}`"
    # elif isinstance(error, errors.SilentError):
    #     # this will fail the interaction hmm
    #     cmd = f'/{ntr.command.qualified_name}' if ntr.command else '?-cmd ntr'
    #     logging.debug(f'Ignoring silent command error raised in application command {cmd}', exc_info=False)
    #     return
    elif isinstance(error, app_commands.CommandSignatureMismatch):
        # TODO: WARN DEVS make title too
        desc = (
            f"**\N{WARNING SIGN} This command's signature is out of date!**\n"
            f"I've warned the developers about this and it will be fixed as soon as possible."
        )
    elif isinstance(error, app_commands.CommandNotFound):
        desc = (  # TODO: WARN DEVS make title too
            # TODO: maybe link our server there or create a new server for the bot support?
            '**Sorry, but somehow this slash command does not exist anymore.**\n'
            f'If you think this command should exist, please ask about it using {const.Slash.feedback} command.'
        )
    else:
        desc = (
            "I've notified my developer and we'll hopefully get it fixed soon.\n"
            "Sorry for the inconvenience! {0} {0} {0}".format(const.Emote.DankL)
        )

        where = f'/{ntr.command.qualified_name}' if ntr.command else '?-cmd ntr'
        await ntr.client.exc_manager.register_error(error, ntr, where=f'on_app_command_error {where}')

        mention = ntr.channel_id != ntr.client.hideout.spam_channel_id
        if not mention:
            # well, then I do not need "desc" embed as well
            if not ntr.response.is_done():
                # they error out unanswered anyway if not "is_done":/
                await ntr.response.send_message(':x', ephemeral=True)
            return

    e = discord.Embed(colour=const.Colour.error())
    if error_type:
        e.set_author(name=error_type)
    e.description = desc
    if not ntr.response.is_done():
        await ntr.response.send_message(embed=e, ephemeral=True)
    else:
        await ntr.followup.send(embed=e, ephemeral=True)


async def setup(bot: AluBot):
    bot.old_tree_error = bot.tree.on_error
    bot.tree.on_error = on_app_command_error


async def teardown(bot: AluBot):
    bot.tree.on_error = bot.old_tree_error
    del bot.logging_handler