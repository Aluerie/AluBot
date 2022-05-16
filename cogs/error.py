from discord import Embed, ApplicationContext, ApplicationCommandInvokeError
from discord.ext import commands

from utils import database as db
from utils.format import display_time
from utils.var import Clr, rmntn
from utils.dcordtools import send_traceback


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Info'

    async def command_error_work(self, ctx, error):
        embed = Embed(color=Clr.error)
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        elif isinstance(error, ApplicationCommandInvokeError):
            error = error.original
        embed.set_author(name=error.__class__.__name__)

        match error:
            case commands.BadFlagArgument():
                embed.description = f'Bad flag argument: {error.flag.name}'
            case commands.MissingFlagArgument():
                embed.description = f'You forgot to provide a value to this flag: `{error.flag.name}`'
            case commands.TooManyFlags():
                embed.description = \
                    f'You provided way too many values ({len(error.values)})' \
                    f' for this flag: `{error.flag.name}`'
            case commands.errors.MissingRequiredFlag():
                embed.description = f'Please, provide this flag: `{error.flag.name}`'
            case commands.MissingRequiredArgument():
                embed.description = f'Please, provide this argument: `{error.param.name}`'
            case commands.TooManyArguments():
                embed.description = 'Please, double check your arguments to the command'
            case commands.MessageNotFound():
                embed.description = f'Bad argument: {error.argument}'
            case commands.MemberNotFound():
                embed.description = f'Bad argument: {error.argument}'
            case commands.UserNotFound():
                embed.description = f'Bad argument: {error.argument}'
            case commands.ChannelNotFound():
                embed.description = f'Bad argument: {error.argument}'
            case commands.ChannelNotReadable():
                embed.description = f'Bad argument: {error.argument}'
            case commands.BadColourArgument():
                embed.description = f'Bad argument: {error.argument}'
            case commands.RoleNotFound():
                embed.description = f'Bad argument: {error.argument}'
            case commands.BadInviteArgument():
                embed.description = f'Bad argument'
            case commands.EmojiNotFound():
                embed.description = f'Bad argument: {error.argument}'
            case commands.PartialEmojiConversionFailure():
                embed.description = f'Bad argument: {error.argument}'
            case commands.BadBoolArgument():
                embed.description = f'Bad argument: {error.argument}'
            case commands.BadLiteralArgument():
                embed.description = \
                    f'Only these choices are valid for parameter `{error.param.name}`:\n `{", ".join(error.literals)}`'
            case commands.MissingPermissions():
                embed.description = f'Missing permissions: {error.missing_perms}'
            case commands.BotMissingPermissions():
                embed.description = f'Missing permissions: {error.missing_perms}'
            case commands.MissingRole():
                embed.description = f'Missing role: {rmntn(error.missing_role)}'
            case commands.BotMissingRole():
                embed.description = f'Missing role: {rmntn(error.missing_role)}'
            case commands.MissingAnyRole():
                embed.description = f'Missing roles: {", ".join([rmntn(id_) for id_ in error.missing_roles])}'
            case commands.BotMissingAnyRole():
                embed.description = f'Missing roles: {", ".join([rmntn(id_) for id_ in error.missing_roles])}'
            case commands.NSFWChannelRequired():
                embed.description = "Ask Irene to make that channel NSFW friendly"
            case commands.CommandNotFound():
                if not ctx.bot.yen and ctx.prefix != db.get_value(db.g, ctx.guild.id, 'prefix'):
                    return
                embed.description = f"Please, double-check, did you make a typo? Or use `{ctx.prefix}help`"
            case commands.NotOwner():
                embed.description = f"Sorry, only Bot Owner is allowed to use this command"
            case commands.PrivateMessageOnly():
                embed.description = f"The command is only for usage in private messages with the bot. " \
                                    f"Please, send a dm to {self.bot.user.mention}"
            case commands.NoPrivateMessage():
                embed.description = f"The command is only for usage in server channels. " \
                                    f"Please, go to a server where {self.bot.user.mention} is invited."
            case commands.CommandOnCooldown():
                embed.description = f"Please retry in {display_time(error.retry_after, 3)}"
            case _:
                embed.description = \
                    f"Oups, some error but I already notified my dev about it. The original exception:\n" \
                    f"```python\n{error}```"

                err_embed = Embed(colour=Clr.error)
                prefix = getattr(ctx, 'clean_prefix', '/')
                if isinstance(ctx, commands.Context):
                    ch = ctx.channel
                    jump_url = ctx.message.jump_url
                elif isinstance(ctx, ApplicationContext):
                    ch = ctx.interaction.channel
                    msg = await ctx.interaction.original_message()
                    jump_url = msg.jump_url
                else:
                    ch = 'unknown'
                    jump_url = ''

                err_embed.description = \
                    f'{ctx.author} [triggered error using]({jump_url}) ' \
                    f'`{prefix}{ctx.command.qualified_name}` in {ch.mention}'
                await send_traceback(error, self.bot, embed=err_embed)
        return embed

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not getattr(ctx, 'error_handled', False):
            embed = await self.command_error_work(ctx, error)
            return await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if not getattr(ctx, 'error_handled', False):
            embed = await self.command_error_work(ctx, error)
            return await ctx.respond(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))
