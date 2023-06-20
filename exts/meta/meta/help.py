from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, NamedTuple, Literal, Sequence

import discord
from discord import app_commands
from discord.ext import commands, menus

from utils import AluCog, AluContext, ExtCategory, aluloop, const, pagination

if TYPE_CHECKING:
    from utils import AluBot

class HelpPageData(NamedTuple):
    cog: AluCog | Literal['front_page']
    cmds: Optional[Sequence[commands.Command]]
    cog_page: int


class AluHelpPageSource(menus.ListPageSource):
    pass


class AluHelpPages(pagination.Paginator):
    source: AluHelpPageSource

    def __init__(self, ctx: AluContext, source: AluHelpPageSource):
        super().__init__(ctx, source)


class AluHelp(commands.HelpCommand):
    context: AluContext

    def __init__(self, starting_category: int  = 0) -> None:
        super().__init__(
            verify_checks=False,  # TODO: idk we need to decide this
            command_attrs={
                'hidden': False,
                'help': 'Show `help` menu for the bot.',
                'usage': '[command/section]',
            },
        )
        self.starting_category: int = starting_category
    
    def get_bot_mapping(self) -> Dict[Optional[ExtCategory], Dict[AluCog, List[commands.Command]]]:
        """Retrieves the bot mapping passed to :meth:`send_bot_help`."""

        # TODO: include solo slash commands and Context Menu commands.
        mapping = {
            category: {cog: cog.get_commands() for cog in cog_list}
            for category, cog_list in self.context.bot.ext_categories.items()
        }
        return dict(sorted(mapping.items()))

    async def send_bot_help(self, mapping: Dict[Optional[ExtCategory], Dict[AluCog, List[commands.Command]]]):
        await self.context.typing()

        print(mapping)
        help_data: List[HelpPageData] = [HelpPageData(cog='front_page', cmds=None, cog_page=0)]
        
        await self.context.reply('wowzers')


class AluHelpCog(AluCog):
    """Help command."""

    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        bot.help_command = AluHelp()
        bot.help_command.cog = self
        self._original_help_command: Optional[commands.HelpCommand] = bot.help_command

    async def cog_load(self) -> None:
        self.load_help_info.start()

    async def cog_unload(self) -> None:
        self.load_help_info.cancel()
        self.bot.help_command = self._original_help_command

    @app_commands.command(name='help')
    @app_commands.describe(command='Command name to get help about.')
    async def slash_help(self, ntr: discord.Interaction, *, command: Optional[str]):
        """Show help menu for the bot."""
        # todo: starting category
        my_help = AluHelp()
        my_help.context = ctx = await AluContext.from_interaction(ntr)
        await my_help.command_callback(ctx, command=command)

    @aluloop(count=1)
    async def load_help_info(self):
        # auto-syncing is bad, but is auto-fetching commands bad to fill the cache?
        # If I ever get rate-limited here then we will think :thinking:
        await self.bot.tree.fetch_commands()

        if not self.bot.test:
            # announce to community/hideout that we logged in
            # from testing purposes it means we can use help with [proper slash mentions (if synced).
            e = discord.Embed(colour=const.Colour.prpl())
            e.description = f'Logged in as {self.bot.user.name}'
            await self.hideout.spam.send(embed=e)
            e.set_footer(text='Finished updating/rebooting')
            await self.community.bot_spam.send(embed=e)


async def setup(bot: AluBot):
    await bot.add_cog(AluHelpCog(bot))
