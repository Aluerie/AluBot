from __future__ import annotations

from typing import TYPE_CHECKING, Any

from discord import app_commands

from bot import AluCog, AluContext

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


class AluHelpCog(AluCog):
    """Help command."""

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        if bot.help_command:
            bot.help_command.cog = self

    @app_commands.command(name="help")
    @app_commands.describe(query="Command/Section/Category name to get help about.")
    async def slash_help(self, interaction: AluInteraction, *, query: str | None) -> None:
        """Show help menu for the bot."""
        ctx = await AluContext.from_interaction(interaction)
        if query:
            await ctx.send_help(query)
        else:
            await ctx.send_help()
        # todo: starting category
        # my_help = AluHelp()
        # my_help.context = ctx = await AluContext.from_interaction(ntr)
        # await my_help.command_callback(ctx, command=command)

    # @commands.is_owner()
    # @commands.command(hidden=True)
    # async def devhelp(self, ctx: AluContext, *, query: str | None) -> None:
    #     """Show dev help menu for the bot."""
    #     my_help = AluHelp(show_hidden=True)
    #     my_help.context = ctx
    #     await my_help.command_callback(ctx, command=query)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(AluHelpCog(bot))
