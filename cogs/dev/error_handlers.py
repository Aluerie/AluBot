from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

from utils import const

from ._base import DevBaseCog

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class ErrorHandlers(DevBaseCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: AluContext, error: Exception) -> None:
        """|coro|

        A handler called when an error is raised while invoking a command.

        Parameters
        ----------
        ctx: :class:`AluContext`
            The context for the command.
        error: :class:`Exception`
            The error that was raised or passed down by chain like `commands.HybridCommandError`
        """
        if ctx.is_error_handled is True:
            return

        error_type = error.__class__.__name__
        match error:
            case commands.HybridCommandError() | commands.CommandInvokeError() | app_commands.CommandInvokeError():
                # we aren't interested in the chain.
                return await self.on_command_error(ctx, error.original)
            case commands.CommandNotFound():
                if ctx.prefix in ['/', f'<@{self.bot.user.id}> ', f'<@!{self.bot.user.id}> ']:
                    return
                # TODO: make a fuzzy search in here to recommend the command that user wants
                desc = f"Please, double-check, did you make a typo? Or use `{ctx.prefix}help`"

            case _:
                cmd_kwargs = ' '.join([f'{k}: {v}' for k, v in ctx.kwargs.items()])

                if ctx.interaction:
                    jump_url, cmd_text = '', f'/{ctx.command.qualified_name}'
                else:
                    jump_url, cmd_text = ctx.message.jump_url, ctx.message.content

                error_embed = discord.Embed(description=f'{cmd_text}\n{cmd_kwargs}', colour=const.Colour.error())

                # if I'm myself in the channel testing commands - I don't need mention or redirection.
                mention = ctx.channel.id != ctx.bot.hideout.spam_channel_id
                if mention:
                    msg = f'{ctx.author} triggered error in {ctx.channel}'
                    error_embed.set_author(name=msg, url=jump_url, icon_url=ctx.author.display_avatar.url)
                await self.bot.send_exception(error, embed=error_embed, mention=mention)

                if not mention:
                    # then I do not need "I notified my dev" embed
                    if ctx.interaction:  # they error out unanswered
                        await ctx.reply(':(', ephemeral=True)
                    return
                else:
                    desc = (
                        "I've notified my developer and we'll hopefully get it fixed soon.\n"
                        "Sorry for the inconvenience! {0} {0} {0}".format(const.Emote.DankL)
                    )
                    error_type = 'Oups...Unexpected error!'

        e = discord.Embed(color=const.Colour.error(), description=desc).set_author(name=error_type)
        await ctx.reply(embed=e, ephemeral=True)


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


async def on_app_command_error(ntr: discord.Interaction, error: discord.app_commands.AppCommandError, /) -> None:
    command = ntr.command

    if command is not None:
        if command._has_any_error_handlers():
            return

async def setup(bot: AluBot):
    commands.Bot.on_error = on_error
    await bot.add_cog(ErrorHandlers(bot))
    bot.old_tree_error = bot.tree.on_error  # type: ignore
    bot.tree.on_error = on_app_command_error


async def teardown(bot: AluBot):
    commands.Bot.on_error = old_on_error
    bot.tree.on_error = bot.old_tree_error  # type: ignore
