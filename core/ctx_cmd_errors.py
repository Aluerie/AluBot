from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import errors, formats, helpers

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext


async def on_command_error(ctx: AluContext, error: commands.CommandError | Exception) -> None:
    """Handler called when an error is raised while invoking a ctx command."""
    if ctx.is_error_handled is True:
        return

    # error handler working variables
    desc = "No description"
    is_unexpected = False
    mention = True

    # error handler itself.

    # CHAINED ERRORS
    if isinstance(error, (commands.HybridCommandError, commands.CommandInvokeError, app_commands.CommandInvokeError)):
        # we aren't interested in the chain traceback.
        return await on_command_error(ctx, error.original)

    # MY OWN ERRORS
    elif isinstance(error, errors.AluBotError):
        # These errors are generally raised in code by myself or by my code with an explanation text as `error`
        # AluBotError subclassed exceptions are all mine.
        desc = f"{error}"

    # BAD ARGUMENT SUBCLASSED ERRORS
    elif isinstance(error, commands.EmojiNotFound):
        desc = f"Sorry! `{error.argument}` is not a custom emote."
    elif isinstance(error, commands.BadArgument):
        desc = f"{error}"

    elif isinstance(error, commands.MissingRequiredArgument):
        desc = f"Please, provide this argument:\n`{error.param.name}`"
    elif isinstance(error, commands.CommandNotFound):
        if ctx.prefix in ["/", f"<@{ctx.bot.user.id}> ", f"<@!{ctx.bot.user.id}> "]:
            return
        if ctx.prefix == "$" and ctx.message.content[1].isdigit():
            # "$200 for this?" 2 is `ctx.message.content[1]`
            # prefix commands should not start with digits
            return
        # TODO: make a fuzzy search in here to recommend the command that user wants
        desc = f"Please, double-check, did you make a typo? Or use `{ctx.prefix}help`"
    elif isinstance(error, commands.CommandOnCooldown):
        desc = f"Please retry in `{formats.human_timedelta(error.retry_after, mode='brief')}`"
    elif isinstance(error, commands.NotOwner):
        desc = f"Sorry, only {ctx.bot.owner} as the bot developer is allowed to use this command."
    elif isinstance(error, commands.MissingRole):
        desc = f"Sorry, only {error.missing_role} are able to use this command."
    elif isinstance(error, commands.CheckFailure):
        desc = f"{error}"

    # elif isinstance(error, errors.SilentError):
    #     # this will fail the interaction hmm
    #     return
    else:
        # error is unhandled/unclear and thus developers need to be notified about it.
        is_unexpected = True

        cmd_name = f"{ctx.clean_prefix}{ctx.command.qualified_name if ctx.command else 'non-cmd'}"
        metadata_embed = (
            discord.Embed(
                colour=0x890620,
                title=f"Error with `{ctx.clean_prefix}{ctx.command}`",
                url=ctx.message.jump_url,
                description=textwrap.shorten(ctx.message.content, width=1024),
                # timestamp=ctx.message.created_at,
            )
            .set_author(
                name=f"@{ctx.author} in #{ctx.channel} ({ctx.guild.name if ctx.guild else "DM Channel"})",
                icon_url=ctx.author.display_avatar,
            )
            .add_field(
                name="Command Args",
                value=(
                    "```py\n" + "\n".join(f"[{name}]: {value!r}" for name, value in ctx.kwargs.items()) + "```"
                    if ctx.kwargs
                    else "```py\nNo arguments```"
                ),
                inline=False,
            )
            .add_field(
                name="Snowflake Ids",
                value=(
                    "```py\n"
                    f"author  = {ctx.author.id}\n"
                    f"channel = {ctx.channel.id}\n"
                    f"guild   = {ctx.guild.id if ctx.guild else "DM Channel"}```"
                ),
            )
            .set_footer(
                text=f"on_command_error: {cmd_name}",
                icon_url=ctx.guild.icon if ctx.guild else ctx.author.display_avatar,
            )
        )
        mention = bool(ctx.channel.id != ctx.bot.hideout.spam_channel_id)
        await ctx.bot.exc_manager.register_error(error, metadata_embed, mention=mention)

    response_embed = helpers.error_handler_response_embed(error, is_unexpected, desc, mention)
    await ctx.reply(embed=response_embed, ephemeral=True)


async def setup(bot: AluBot) -> None:
    bot.add_listener(on_command_error)


async def teardown(bot: AluBot) -> None:
    bot.remove_listener(on_command_error)


"""

match error:
    case app_commands.TransformerError():
        maybe_original_error = error.__cause__
        if maybe_original_error:
            return await self.error_handler_worker(ctx, maybe_original_error, _type=_type)
        else:
            desc = f'{error}'

this is for missing required argument

if (  # todo: this is wonky, we probably should just overwrite it on command basis for more clarity
    getattr(error.param, 'converter', None)
    and inspect.isclass(error.param.converter)
    and issubclass(error.param.converter, commands.FlagConverter)
):
    desc += (
        '\n\nThis is flag based argument. '
        'Remember, commands with those are used together with flag-keywords , i.e.\n'
        '`$dota stream add twitch: gorgc steam: 123`\n'
        'meaning you need to specify that `twitch:` flag is `gorgc` '
        'similarly how you type `from: @Eileen` in Discord Search feature'
    )

TODO: Uncomment these errors as we reinvest the code.
case commands.BadFlagArgument():
    desc = f'`{error.flag.name}: {error.argument}`\n\n{error.original}'
case commands.MissingFlagArgument():
    desc = f'You forgot to provide a value to this flag:\n`{error.flag.name}`'
case commands.TooManyFlags():
    desc = f'You provided way too many values ({len(error.values)}) for this flag:\n`{error.flag.name}`'
case commands.errors.MissingRequiredFlag():
    desc = f'Please, provide this flag:\n`{error.flag.name}`'


case commands.TooManyArguments():
    desc = 'Please, double check your arguments for the command'
case commands.MessageNotFound():
    desc = f'Bad argument: {error.argument}'
case commands.MemberNotFound():
    desc = f'This is not a valid member argument: `{error.argument}`'
case commands.UserNotFound():
    desc = f'Bad argument: {error.argument}'
case commands.ChannelNotFound():
    desc = f'Bad argument: {error.argument}'
case commands.ChannelNotReadable():
    desc = f'Bad argument: {error.argument}'
case commands.BadColourArgument():
    desc = f'Bad argument: {error.argument}'
case commands.RoleNotFound():
    desc = f'Bad argument: {error.argument}'
case commands.BadInviteArgument():
    desc = f'Bad argument'
case commands.PartialEmojiConversionFailure():
    desc = f'Bad argument: {error.argument}'
case commands.BadBoolArgument():
    desc = f'Bad argument: {error.argument}'
case commands.BadLiteralArgument():
    desc = (
        f'Only these choices are valid for parameter `{error.param.name}`:\n `{", ".join(error.literals)}`'
    )
case commands.MissingPermissions():
    desc = f'Missing permissions: {", ".join(error.missing_permissions)}'
case commands.BotMissingPermissions():
    desc = f'Bot is missing permissions: {", ".join(error.missing_permissions)}'

case commands.BotMissingRole():
    desc = f'Missing role: <@&{error.missing_role}'
case commands.MissingAnyRole():
    desc = f'Missing roles: {", ".join([f"<@&{id_}>" for id_ in error.missing_roles])}'
case commands.BotMissingAnyRole():
    desc = f'Missing roles: {", ".join([f"<@&{id_}>" for id_ in error.missing_roles])}'
case commands.NSFWChannelRequired():
    desc = "Ask Aluerie to make that channel NSFW friendly"
case commands.PrivateMessageOnly():
    desc = (
        f"The command is only for usage in private messages with the bot. "
        f"Please, send a dm to {self.bot.user.mention}"
    )
case commands.NoPrivateMessage():
    desc = (
        f"The command is only for usage in server channels. "
        f"Please, go to a server where {self.bot.user.mention} is invited."
    )
"""
