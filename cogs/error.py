from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, app_commands
from discord.ext import commands

from utils import database as db
from utils.context import Context
from utils.format import display_time
from utils.var import Clr, rmntn
from utils.distools import send_traceback

if TYPE_CHECKING:
    from discord import Interaction


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error

    async def command_error_work(self, ctx, error):
        if isinstance(error, commands.HybridCommandError):
            error = error.original
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original

        match error:
            case commands.BadFlagArgument():
                desc = \
                    f'`{error.flag.name}: {error.argument}`' \
                    f'\n\n{error.original}'
            case commands.MissingFlagArgument():
                desc = f'You forgot to provide a value to this flag:\n`{error.flag.name}`'
            case commands.TooManyFlags():
                desc = \
                    f'You provided way too many values ({len(error.values)})' \
                    f' for this flag:\n`{error.flag.name}`'
            case commands.errors.MissingRequiredFlag():
                desc = \
                    f'Please, provide this flag:\n`{error.flag.name}`'
            case commands.MissingRequiredArgument():
                desc = f'Please, provide this argument:\n`{error.param.name}`'
                if hasattr(error.param, 'converter') and issubclass(error.param.converter, commands.FlagConverter):
                    desc += \
                        '\n\nThis is flag based argument. ' \
                        'Remember, commands with those are used together with flag-keywords , i.e.\n' \
                        '`$dota stream add twitch: gorgc steam: 123`\n' \
                        'meaning you need to specify that `twitch:` flag is `gorgc` ' \
                        'similarly how you type `from: @Eileen` in Discord Search feature'
            case commands.TooManyArguments():
                desc = 'Please, double check your arguments to the command'
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
                desc = f'Missing role: {rmntn(error.missing_role)}'
            case commands.BotMissingRole():
                desc = f'Missing role: {rmntn(error.missing_role)}'
            case commands.MissingAnyRole():
                desc = f'Missing roles: {", ".join([rmntn(id_) for id_ in error.missing_roles])}'
            case commands.BotMissingAnyRole():
                desc = f'Missing roles: {", ".join([rmntn(id_) for id_ in error.missing_roles])}'
            case commands.NSFWChannelRequired():
                desc = "Ask Aluerie to make that channel NSFW friendly"
            case commands.CommandNotFound():
                if not ctx.bot.yen and ctx.prefix != db.get_value(db.ga, ctx.guild.id, 'prefix'):
                    return
                desc = f"Please, double-check, did you make a typo? Or use `{ctx.prefix}help`"
            case commands.NotOwner():
                desc = f"Sorry, only Bot Owner is allowed to use this command"
            case commands.PrivateMessageOnly():
                desc = \
                    f"The command is only for usage in private messages with the bot. " \
                    f"Please, send a dm to {self.bot.user.mention}"
            case commands.NoPrivateMessage():
                desc = \
                    f"The command is only for usage in server channels. " \
                    f"Please, go to a server where {self.bot.user.mention} is invited."
            case commands.CommandOnCooldown() | app_commands.CommandOnCooldown():
                desc = f"Please retry in `{display_time(error.retry_after, 3)}`"
            case commands.CheckFailure():
                desc = f'{error}'
            case _:
                desc = \
                    f"Oups, some error but I already notified my dev about it.\n The original exception:\n" \
                    f"```py\n{error}```"

                cmd_kwargs = ' '.join([f'{k}: {v}' for k, v in ctx.kwargs.items()])
                if ctx.interaction:
                    jump_url = ''
                    cmd_text = f'/{ctx.command.qualified_name}'
                else:
                    jump_url = ctx.message.jump_url
                    cmd_text = ctx.message.content

                err_embed = Embed(
                    colour=Clr.error,
                    description=f'{cmd_text}\n{cmd_kwargs}'
                ).set_author(
                    name=
                    f'{ctx.author} triggered error in {ctx.channel}',
                    url=jump_url,
                    icon_url=ctx.author.avatar.url
                )
                await send_traceback(error, self.bot, embed=err_embed)
        return Embed(
            color=Clr.error,
            description=desc,
        ).set_author(name=error.__class__.__name__)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        if not getattr(ctx, 'error_handled', False):
            embed = await self.command_error_work(ctx, error)
            return await ctx.reply(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_app_command_error(self, ntr: Interaction, error):
        if not getattr(ntr, 'error_handled', False):
            ctx = await Context.from_interaction(ntr)
            embed = await self.command_error_work(ctx, error)
            return await ntr.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(CommandErrorHandler(bot))
