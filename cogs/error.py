from __future__ import annotations
from typing import TYPE_CHECKING

import inspect

import discord
from discord import app_commands
from discord.ext import commands

from .utils.context import Context
from .utils.formats import human_timedelta
from .utils.var import Clr, Cid, Ems

if TYPE_CHECKING:
    from .utils.bot import AluBot


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        bot.tree.on_error = self.on_app_command_error

    async def command_error_work(self, ctx: Context, error) -> None:
        while isinstance(
                error,
                (commands.HybridCommandError, commands.CommandInvokeError, app_commands.CommandInvokeError,)
        ):  # circle to the actual error throughout all the chains
            error = error.original

        error_type = error.__class__.__name__
        handled, mention = True, True
        match error:
            case commands.BadFlagArgument():
                desc = f'`{error.flag.name}: {error.argument}`\n\n{error.original}'
            case commands.MissingFlagArgument():
                desc = f'You forgot to provide a value to this flag:\n`{error.flag.name}`'
            case commands.TooManyFlags():
                desc = f'You provided way too many values ({len(error.values)}) for this flag:\n`{error.flag.name}`'
            case commands.errors.MissingRequiredFlag():
                desc = f'Please, provide this flag:\n`{error.flag.name}`'
            case commands.MissingRequiredArgument():
                desc = f'Please, provide this argument:\n`{error.param.name}`'
                if getattr(error.param, 'converter', None) and \
                        inspect.isclass(error.param.converter) and \
                        issubclass(error.param.converter, commands.FlagConverter):
                    desc += (
                        '\n\nThis is flag based argument. '
                        'Remember, commands with those are used together with flag-keywords , i.e.\n'
                        '`$dota stream add twitch: gorgc steam: 123`\n'
                        'meaning you need to specify that `twitch:` flag is `gorgc` '
                        'similarly how you type `from: @Eileen` in Discord Search feature'
                    )
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
                desc = \
                    f'Only these choices are valid for parameter `{error.param.name}`:\n `{", ".join(error.literals)}`'
            case commands.BadArgument():
                desc = f'{error}'
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
            case commands.CommandNotFound():
                if ctx.prefix in ['/', f'<@{self.bot.user.id}> ', f'<@!{self.bot.user.id}> ']:
                    return
                desc = f"Please, double-check, did you make a typo? Or use `{ctx.prefix}help`"
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
            case commands.CommandOnCooldown() | app_commands.CommandOnCooldown():
                desc = f"Please retry in `{human_timedelta(error.retry_after, brief=True)}`"
            case commands.CheckFailure():
                desc = f'{error}'
            case _:
                handled = False

                desc = (
                    "I've notified my creator and we'll hopefully get it fixed soon. \n"
                    "Sorry for the inconvenience! {0} {0} {0}".format(Ems.DankL)
                )
                error_type = 'Oups...Unexpected error!'

                cmd_kwargs = ' '.join([f'{k}: {v}' for k, v in ctx.kwargs.items()])
                if ctx.interaction:
                    jump_url, cmd_text = '', f'/{ctx.command.qualified_name}'
                else:
                    jump_url, cmd_text = ctx.message.jump_url, ctx.message.content

                error_e = discord.Embed(description=f'{cmd_text}\n{cmd_kwargs}', colour=Clr.error)
                if not self.bot.test:
                    error_e.set_author(
                        name=f'{ctx.author} triggered error in {ctx.channel}',
                        url=jump_url,
                        icon_url=ctx.author.display_avatar.url
                    )
                mention = (ctx.channel.id != Cid.spam_me)
                await self.bot.send_traceback(error, embed=error_e, mention=mention)

        # send the error
        if not handled and self.bot.test and not mention:
            if ctx.interaction:  # they error out unanswered
                await ctx.reply(':(', ephemeral=True)
            else:
                return
        else:
            e = discord.Embed(color=Clr.error, description=desc).set_author(name=error_type)
            await ctx.reply(embed=e, ephemeral=True)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        if not getattr(ctx, 'error_handled', False):
            await self.command_error_work(ctx, error)

    @commands.Cog.listener()
    async def on_app_command_error(self, ntr: discord.Interaction, error):
        if not getattr(ntr, 'error_handled', False):
            ctx = await Context.from_interaction(ntr)
            await self.command_error_work(ctx, error)


async def setup(bot: AluBot):
    await bot.add_cog(CommandErrorHandler(bot))
