from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import app_commands
from discord.ext import commands

from utils import const
from utils.times import BadTimeTransform
from utils.translator import TranslateError

from ._base import DevBaseCog

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class ErrorHandlers(DevBaseCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = self.on_app_command_error

    async def cog_unload(self):
        tree = self.bot.tree
        tree.on_error = self._old_tree_error

    async def error_handler_worker(
        self, ctx: AluContext, error: Exception, _type: Literal['on_app_command_error', 'on_command_error']
    ):
        """|coro|

        Function that called by both `on_command_error` and `on_app_command_error`.

        Development wise - it's easier to throw both error handlers into the same worker,
        because some errors are shared or have same responses like `CommandOnCooldown`,
        especially when we include `HybridCommandError`
        or my own custom errors like `TranslationError`.

        This structure kinda transforms the whole process into "eh it all will sort **itself** out".

        And this way I can lazily raise `commands.BarArgument` everywhere and pretend it's fine
        since it will say "BadArgument" in the error because there is no analogy for this in `app_commands`.

        Parameters
        ----------
        ctx: :class:`AluContext`
            The context for the command/app_command.
        error: :class:`Exception`
            The error that was raised or passed down in chain by errors like `commands.HybridCommandError`.
        _type: :class: `Literal['on_app_command_error', 'on_command_error']`
            Name of the error handler triggered this worker.
        """
        if ctx.is_error_handled is True:
            return

        error_type = error.__class__.__name__
        warn_developers = False
        include_traceback = True
        match error:
            case commands.HybridCommandError() | commands.CommandInvokeError() | app_commands.CommandInvokeError():
                # we aren't interested in the chain traceback.
                return await self.error_handler_worker(ctx, error.original, _type=_type)
            case commands.BadArgument() | commands.CheckFailure() | TranslateError() | BadTimeTransform():
                # These errors are generally raised in code by myself with an explanation text as `error`
                desc = f'{error}'
            case app_commands.CommandNotFound():
                desc = (
                    # TODO: maybe link our server there or create a new server for the bot support?
                    '**Sorry, but somehow this slash command does not exist anymore.**'
                    '\nIf you think this command should exist, please ask about it using `/feedback` command.'
                )
            case app_commands.CommandSignatureMismatch():
                warn_developers = True
                include_traceback = False
                desc = (
                    f"**\N{WARNING SIGN} This command's signature is out of date!**\n"
                    f"I've warned the developers about this and it will be fixed as soon as possible",
                )
            case commands.CommandNotFound():
                if ctx.prefix in ['/', f'<@{self.bot.user.id}> ', f'<@!{self.bot.user.id}> ']:
                    return
                # TODO: make a fuzzy search in here to recommend the command that user wants
                desc = f"Please, double-check, did you make a typo? Or use `{ctx.prefix}help`"
            case commands.CommandOnCooldown() | app_commands.CommandOnCooldown():
                desc = f"Please retry in `{self.bot.formats.human_timedelta(error.retry_after, brief=True)}`"

            # TODO: Uncomment these errors as we reinvest the code.
            # case commands.BadFlagArgument():
            #     desc = f'`{error.flag.name}: {error.argument}`\n\n{error.original}'
            # case commands.MissingFlagArgument():
            #     desc = f'You forgot to provide a value to this flag:\n`{error.flag.name}`'
            # case commands.TooManyFlags():
            #     desc = f'You provided way too many values ({len(error.values)}) for this flag:\n`{error.flag.name}`'
            # case commands.errors.MissingRequiredFlag():
            #     desc = f'Please, provide this flag:\n`{error.flag.name}`'
            # case commands.MissingRequiredArgument():
            #     desc = f'Please, provide this argument:\n`{error.param.name}`'
            #     if (
            #         getattr(error.param, 'converter', None)
            #         and inspect.isclass(error.param.converter)
            #         and issubclass(error.param.converter, commands.FlagConverter)
            #     ):
            #         desc += (
            #             '\n\nThis is flag based argument. '
            #             'Remember, commands with those are used together with flag-keywords , i.e.\n'
            #             '`$dota stream add twitch: gorgc steam: 123`\n'
            #             'meaning you need to specify that `twitch:` flag is `gorgc` '
            #             'similarly how you type `from: @Eileen` in Discord Search feature'
            #         )
            # case commands.TooManyArguments():
            #     desc = 'Please, double check your arguments for the command'
            # case commands.MessageNotFound():
            #     desc = f'Bad argument: {error.argument}'
            # case commands.MemberNotFound():
            #     desc = f'This is not a valid member argument: `{error.argument}`'
            # case commands.UserNotFound():
            #     desc = f'Bad argument: {error.argument}'
            # case commands.ChannelNotFound():
            #     desc = f'Bad argument: {error.argument}'
            # case commands.ChannelNotReadable():
            #     desc = f'Bad argument: {error.argument}'
            # case commands.BadColourArgument():
            #     desc = f'Bad argument: {error.argument}'
            # case commands.RoleNotFound():
            #     desc = f'Bad argument: {error.argument}'
            # case commands.BadInviteArgument():
            #     desc = f'Bad argument'
            # case commands.EmojiNotFound():
            #     desc = f'Bad argument: {error.argument}'
            # case commands.PartialEmojiConversionFailure():
            #     desc = f'Bad argument: {error.argument}'
            # case commands.BadBoolArgument():
            #     desc = f'Bad argument: {error.argument}'
            # case commands.BadLiteralArgument():
            #     desc = (
            #         f'Only these choices are valid for parameter `{error.param.name}`:\n `{", ".join(error.literals)}`'
            #     )
            # case commands.MissingPermissions():
            #     desc = f'Missing permissions: {", ".join(error.missing_permissions)}'
            # case commands.BotMissingPermissions():
            #     desc = f'Bot is missing permissions: {", ".join(error.missing_permissions)}'
            # case commands.MissingRole():
            #     desc = f'Missing role: <@&{error.missing_role}>'
            # case commands.BotMissingRole():
            #     desc = f'Missing role: <@&{error.missing_role}'
            # case commands.MissingAnyRole():
            #     desc = f'Missing roles: {", ".join([f"<@&{id_}>" for id_ in error.missing_roles])}'
            # case commands.BotMissingAnyRole():
            #     desc = f'Missing roles: {", ".join([f"<@&{id_}>" for id_ in error.missing_roles])}'
            # case commands.NSFWChannelRequired():
            #     desc = "Ask Aluerie to make that channel NSFW friendly"
            # case commands.NotOwner():
            #     desc = f'Sorry, only {ctx.bot.owner} as the bot owner is allowed to use this command.'
            # case commands.PrivateMessageOnly():
            #     desc = (
            #         f"The command is only for usage in private messages with the bot. "
            #         f"Please, send a dm to {self.bot.user.mention}"
            #     )
            # case commands.NoPrivateMessage():
            #     desc = (
            #         f"The command is only for usage in server channels. "
            #         f"Please, go to a server where {self.bot.user.mention} is invited."
            #     )

            case _:
                # error is unhandled/unclear and thus the developer needs to be notified.
                warn_developers = True
                desc = (
                    "I've notified my developer and we'll hopefully get it fixed soon.\n"
                    "Sorry for the inconvenience! {0} {0} {0}".format(const.Emote.DankL)
                )
                error_type = 'Oups...Unexpected error!'

        if warn_developers:
            cmd_kwargs = ' '.join([f'{k}: {v}' for k, v in ctx.kwargs.items()])

            if ctx.interaction:
                jump_url, cmd_text = '', f'/{ctx.command.qualified_name}'
            else:
                jump_url, cmd_text = ctx.message.jump_url, ctx.message.content

            error_embed = discord.Embed(description=f'{cmd_text}\n{cmd_kwargs}', colour=const.Colour.error())
            error_embed.set_footer(text=_type)

            # if I'm myself in the channel testing commands - I don't need ping-mention or redirection.
            # just annoyance stuff
            mention = ctx.channel.id != ctx.bot.hideout.spam_channel_id
            if mention:
                msg = f'{ctx.author} triggered error in {ctx.channel}'
                error_embed.set_author(name=msg, url=jump_url, icon_url=ctx.author.display_avatar.url)
            await self.bot.send_exception(
                error, embed=error_embed, mention=mention, include_traceback=include_traceback
            )

            if not mention:
                # well, then I do not need "desc" embed as well
                if ctx.interaction and not ctx.interaction.response.is_done():
                    # they error out unanswered anyway if not "is_done":/
                    await ctx.reply(':(', ephemeral=True)
                return

        e = discord.Embed(color=const.Colour.error(), description=desc).set_author(name=error_type)
        await ctx.reply(embed=e, ephemeral=True)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: AluContext, error: commands.CommandError) -> None:
        """|coro|

        A handler called when an error is raised while invoking a command.

        Parameters
        ----------
        ctx: :class:`AluContext`
            The context for the command.
        error: :class:`commands.CommandError`
            The error that was raised.
        """
        await self.error_handler_worker(ctx, error, _type='on_command_error')

    async def on_app_command_error(self, ntr: discord.Interaction, error: app_commands.AppCommandError, /):
        """|coro|

        A handler called when an error is raised while invoking an app_command.

        Parameters
        ----------
        ctx: :class:`discord.Interaction`
            The interaction for the command.
        error: :class:`app_commands.AppCommandError`
            The error that was raised.
        """

        # TODO: Hmm, idk I still want commands to go through this handler if any error occurs
        # not sure how to achieve analogical to "ctx.is_error_handled" behaviour
        # if command is not None:
        #     if command._has_any_error_handlers():
        #         return
        ctx = await AluContext.from_interaction(ntr)
        await self.error_handler_worker(ctx, error, _type='on_app_command_error')


old_on_error = commands.Bot.on_error


async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
    """|coro|

    Called when an error is raised, and it's not from a command,
    but most likely from an event listener.

    Parameters
    ----------
    event: :class:`str`
        The name of the event that raised the exception.
    args: :class:`Any`
        The positional arguments for the event that raised the exception.
    kwargs: :class:`Any`
        The keyword arguments for the event that raised the exception.
    """

    # Exception Traceback
    (_exc_type, exc, _tb) = sys.exc_info()

    # Event Arguments
    e = discord.Embed(title=f'`{event}`', colour=const.Colour.error_handler())
    e.set_author(name='Event Error')

    args_str = ['```py']
    for index, arg in enumerate(args):
        args_str.append(f'[{index}]: {arg!r}')
    args_str.append('```')
    e.add_field(name='Args', value='\n'.join(args_str), inline=False)

    await self.send_exception(exc, e)


async def setup(bot: AluBot):
    commands.Bot.on_error = on_error
    await bot.add_cog(ErrorHandlers(bot))


async def teardown(bot: AluBot):
    commands.Bot.on_error = old_on_error
