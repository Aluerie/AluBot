from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import const, errors

if TYPE_CHECKING:
    from utils import AluBot, AluContext


async def on_command_error(ctx: AluContext, error: commands.CommandError | Exception):
    """Handler called when an error is raised while invoking a ctx command."""
    if ctx.is_error_handled is True:
        return

    error_type = error.__class__.__name__

    if isinstance(error, (commands.HybridCommandError, commands.CommandInvokeError, app_commands.CommandInvokeError)):
        # we aren't interested in the chain traceback.
        return await on_command_error(ctx, error.original)
    elif isinstance(error, errors.ErroneousUsage):
        # raised by myself but it's not an error per se, thus i dont give error type to the user.
        error_type = None
        desc = f'{error}'
    elif isinstance(error, errors.AluBotException):
        # These errors are generally raised in code by myself or by my code with an explanation text as `error`
        # AluBotException subclassed exceptions are all mine.
        desc = f'{error}'
    elif isinstance(error, commands.BadArgument):
        desc = f'{error}'
    elif isinstance(error, commands.MissingRequiredArgument):
        desc = f'Please, provide this argument:\n`{error.param.name}`'
    elif isinstance(error, commands.CommandNotFound):
        if ctx.prefix in ['/', f'<@{ctx.bot.user.id}> ', f'<@!{ctx.bot.user.id}> ']:
            return
        # TODO: make a fuzzy search in here to recommend the command that user wants
        desc = f"Please, double-check, did you make a typo? Or use `{ctx.prefix}help`"
    elif isinstance(error, commands.CommandOnCooldown):
        desc = f"Please retry in `{ctx.bot.formats.human_timedelta(error.retry_after, brief=True)}`"
    elif isinstance(error, commands.NotOwner):
        desc = f'Sorry, only {ctx.bot.owner} as the bot developer is allowed to use this command.'

    # elif isinstance(error, errors.SilentError):
    #     # this will fail the interaction hmm
    #     return
    else:
        # error is unhandled/unclear and thus developers need to be notified about it.
        where = f'on_command_error {ctx.clean_prefix}{ctx.command.qualified_name}' if ctx.command else 'non-cmd ctx'
        await ctx.bot.exc_manager.register_error(error, ctx, where=where)

        error_type = 'Oups...Unexpected error!'
        desc = (
            "I've notified my developer and we'll hopefully get it fixed soon.\n"
            "Sorry for the inconvenience! {0} {0} {0}".format(const.Emote.DankL)
        )
        mention = ctx.channel.id != ctx.bot.hideout.spam_channel_id
        if not mention:
            # well, then I do not need "desc" embed as well
            if ctx.interaction and not ctx.interaction.response.is_done():
                # they error out unanswered anyway if not "is_done":/
                await ctx.reply(':(', ephemeral=True)
            return

    e = discord.Embed(colour=const.Colour.error(), description=desc)
    if error_type:
        e.set_author(name=error_type)
    await ctx.reply(embed=e, ephemeral=True)


async def setup(bot: AluBot):
    bot.add_listener(on_command_error)


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
case commands.EmojiNotFound():
    desc = f'Bad argument: {error.argument}'
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
case commands.MissingRole():
    desc = f'Missing role: <@&{error.missing_role}>'
case commands.BotMissingRole():
    desc = f'Missing role: <@&{error.missing_role}'
case commands.MissingAnyRole():
    desc = f'Missing roles: {", ".join([f"<@&{id_}>" for id_ in error.missing_roles])}'
case commands.BotMissingAnyRole():
    desc = f'Missing roles: {", ".join([f"<@&{id_}>" for id_ in error.missing_roles])}'
case commands.NSFWChannelRequired():
    desc = "Ask Aluerie to make that channel NSFW friendly"
case commands.NotOwner():
    desc = f'Sorry, only {ctx.bot.owner} as the bot owner is allowed to use this command.'
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
