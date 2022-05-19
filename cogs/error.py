from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, app_commands
from discord.ext import commands

from utils import database as db
from utils.context import Context
from utils.format import display_time
from utils.var import Clr, rmntn
from utils.discord import send_traceback

if TYPE_CHECKING:
    from discord import Interaction


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error
        self.help_category = 'Info'

    async def command_error_work(self, ctx, error):
        em = Embed(color=Clr.error)
        if isinstance(error, commands.HybridCommandError):
            error = error.original
        elif isinstance(error, commands.CommandInvokeError):
            error = error.original
        elif isinstance(error, app_commands.CommandInvokeError):
            error = error.original
        em.set_author(name=error.__class__.__name__)

        match error:
            case commands.BadFlagArgument():
                em.description = f'Bad flag argument: {error.flag.name}'
            case commands.MissingFlagArgument():
                em.description = f'You forgot to provide a value to this flag: `{error.flag.name}`'
            case commands.TooManyFlags():
                em.description = \
                    f'You provided way too many values ({len(error.values)})' \
                    f' for this flag: `{error.flag.name}`'
            case commands.errors.MissingRequiredFlag():
                em.description = f'Please, provide this flag: `{error.flag.name}`'
            case commands.MissingRequiredArgument():
                em.description = f'Please, provide this argument: `{error.param.name}`'
            case commands.TooManyArguments():
                em.description = 'Please, double check your arguments to the command'
            case commands.MessageNotFound():
                em.description = f'Bad argument: {error.argument}'
            case commands.MemberNotFound():
                em.description = f'Bad argument: {error.argument}'
            case commands.UserNotFound():
                em.description = f'Bad argument: {error.argument}'
            case commands.ChannelNotFound():
                em.description = f'Bad argument: {error.argument}'
            case commands.ChannelNotReadable():
                em.description = f'Bad argument: {error.argument}'
            case commands.BadColourArgument():
                em.description = f'Bad argument: {error.argument}'
            case commands.RoleNotFound():
                em.description = f'Bad argument: {error.argument}'
            case commands.BadInviteArgument():
                em.description = f'Bad argument'
            case commands.EmojiNotFound():
                em.description = f'Bad argument: {error.argument}'
            case commands.PartialEmojiConversionFailure():
                em.description = f'Bad argument: {error.argument}'
            case commands.BadBoolArgument():
                em.description = f'Bad argument: {error.argument}'
            case commands.BadLiteralArgument():
                em.description = \
                    f'Only these choices are valid for parameter `{error.param.name}`:\n `{", ".join(error.literals)}`'
            case commands.MissingPermissions():
                em.description = f'Missing permissions: {error.missing_perms}'
            case commands.BotMissingPermissions():
                em.description = f'Missing permissions: {error.missing_perms}'
            case commands.MissingRole():
                em.description = f'Missing role: {rmntn(error.missing_role)}'
            case commands.BotMissingRole():
                em.description = f'Missing role: {rmntn(error.missing_role)}'
            case commands.MissingAnyRole():
                em.description = f'Missing roles: {", ".join([rmntn(id_) for id_ in error.missing_roles])}'
            case commands.BotMissingAnyRole():
                em.description = f'Missing roles: {", ".join([rmntn(id_) for id_ in error.missing_roles])}'
            case commands.NSFWChannelRequired():
                em.description = "Ask Irene to make that channel NSFW friendly"
            case commands.CommandNotFound():
                if not ctx.bot.yen and ctx.prefix != db.get_value(db.g, ctx.guild.id, 'prefix'):
                    return
                em.description = f"Please, double-check, did you make a typo? Or use `{ctx.prefix}help`"
            case commands.NotOwner():
                em.description = f"Sorry, only Bot Owner is allowed to use this command"
            case commands.PrivateMessageOnly():
                em.description = f"The command is only for usage in private messages with the bot. " \
                                    f"Please, send a dm to {self.bot.user.mention}"
            case commands.NoPrivateMessage():
                em.description = f"The command is only for usage in server channels. " \
                                    f"Please, go to a server where {self.bot.user.mention} is invited."
            case commands.CommandOnCooldown() | app_commands.CommandOnCooldown():
                em.description = f"Please retry in {display_time(error.retry_after, 3)}"
            case _:
                em.description = \
                    f"Oups, some error but I already notified my dev about it. The original exception:\n" \
                    f"```py\n{error}```"

                err_embed = Embed(colour=Clr.error)
                err_embed.description = \
                    f'{ctx.author} [triggered error using]({ctx.message.jump_url}) ' \
                    f'`{getattr(ctx, "clean_prefix", "/")}{ctx.command.qualified_name}` in {ctx.channel.mention}'
                await send_traceback(error, self.bot, embed=err_embed)
        return em

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
