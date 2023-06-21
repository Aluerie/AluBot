from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Mapping, NamedTuple, Optional, Sequence, TypedDict

import discord
from discord import app_commands
from discord.ext import commands, menus

from utils import AluCog, AluContext, CategoryPage, aluloop, const, pagination
from utils.formats import human_timedelta

from .._category import MetaCog

if TYPE_CHECKING:
    from utils import AluBot


class PagesDict(TypedDict):
    category: CategoryPage
    cog_pages: List[CogPage]


class CogPage(NamedTuple):
    cog: AluCog | commands.Cog
    cmds: Sequence[commands.Command]
    page_num: int  # page per cog so mostly 0


class HelpPageSource(menus.ListPageSource):
    def __init__(self, data: PagesDict):
        entries = [data['category']] + data['cog_pages']
        super().__init__(entries=entries, per_page=1)

    async def format_page(self, menu: HelpPages, entries: CategoryPage | CogPage):
        e = discord.Embed(colour=const.Colour.prpl())
        e.set_footer(text=f'With love, {menu.help_cmd.context.bot.user.display_name}')
        
        if isinstance(entries, CategoryPage):
            e = entries.help_embed(e)
            return e
        elif isinstance(entries, CogPage):
            cog, cmds, page_num = entries

            
            e.title = cog.qualified_name

            desc = cog.description + '\n\n'
            desc += '\n'.join(menu.help_cmd.get_command_signature(c) for c in cmds)
            e.description = desc
            return e


class HelpSelect(discord.ui.Select):
    def __init__(self, paginator: HelpPages):
        super().__init__(placeholder='Choose help category')
        self.paginator: HelpPages = paginator

        self.__fill_options()

    def __fill_options(self) -> None:
        categories = {cat: pages['category'] for cat, pages in self.paginator.help_data.items()}

        categories = dict(sorted(categories.items(), key=lambda x: categories[x[0]].name))

        for key, category in categories.items():
            self.add_option(
                label=category.name,
                emoji=category.emote,
                description='...',
                value=key,
            )

    async def callback(self, ntr: discord.Interaction[AluBot]):
        pages = HelpPages(ntr, self.paginator.help_cmd, self.paginator.help_data, self.values[0])
        await pages.start(edit_response=True)


class HelpPages(pagination.Paginator):
    source: HelpPageSource

    def __init__(
        self,
        ctx: AluContext | discord.Interaction[AluBot],
        help_cmd: AluHelp,
        help_data: Dict[str, PagesDict],
        category: str,
    ):
        self.help_cmd: AluHelp = help_cmd
        self.help_data: Dict[str, PagesDict] = help_data
        self.category: str = category
        super().__init__(ctx, HelpPageSource(help_data[category]))

        self.add_item(HelpSelect(self))


class AluHelp(commands.HelpCommand):
    context: AluContext

    # todo: idk
    def __init__(self, starting_category: str = 'exts.meta._category') -> None:
        super().__init__(
            verify_checks=False,  # TODO: idk we need to decide this
            command_attrs={
                'hidden': False,
                'help': 'Show `help` menu for the bot.',
                'usage': '[command/section]',
            },
        )
        self.starting_category: str = starting_category

    def get_command_signature(self, command: commands.Command) -> str:
        def signature():
            sign = f' `{command.signature}`' if command.signature else ''
            name = command.name if not getattr(command, 'root_parent') else command.root_parent.name  # type:ignore
            app_command = self.context.bot.tree.get_app_command(name)
            if app_command:
                cmd_mention = f"</{command.qualified_name}:{app_command.id}>"
            else:
                prefix = getattr(self.context, 'clean_prefix', '$')
                cmd_mention = f'`{prefix}{command.qualified_name}`'
            return f'{cmd_mention}{sign}'

        def aliases():
            if len(command.aliases):
                return ' | aliases: ' + '; '.join([f'`{ali}`' for ali in command.aliases])
            return ''

        def cd():
            if command.cooldown is not None:
                return f' | cd: {command.cooldown.rate} per {human_timedelta(command.cooldown.per, strip=True, suffix=False)}'
            return ''

        def check():
            if command.checks:
                res = set(getattr(i, '__doc__') or "mods only" for i in command.checks)
                res = [f"*{i}*" for i in res]
                return f"**!** {', '.join(res)}\n"
            return ''

        def help_str():
            return command.help or 'No documentation'

        return f'\N{BLACK CIRCLE} {signature()}{aliases()}{cd()}\n{check()}{help_str()}'

    def get_bot_mapping(self) -> Dict[CategoryPage, Dict[AluCog | commands.Cog, List[commands.Command]]]:
        """Retrieves the bot mapping passed to :meth:`send_bot_help`."""

        # TODO: include solo slash commands and Context Menu commands.
        categories = self.context.bot.ext_categories

        mapping = {category: {cog: cog.get_commands() for cog in cog_list} for category, cog_list in categories.items()}
        # todo: think how to sort front page to front
        return mapping

    async def send_bot_help(
        self,
        mapping: Dict[CategoryPage, Dict[AluCog | commands.Cog, List[commands.Command]]],
    ):
        await self.context.typing()

        help_data: Dict[str, PagesDict] = dict()
        for category, cog_cmd_dict in mapping.items():
            cat_value = category.value
            help_data[cat_value] = {'category': category, 'cog_pages': []}

            for cog, cmds in cog_cmd_dict.items():
                filtered = await self.filter_commands(cmds, sort=True)
                # if filtered:
                help_data[cat_value]['cog_pages'].append(CogPage(cog=cog, cmds=filtered, page_num=0))

        print(help_data)
        pages = HelpPages(self.context, self, help_data, self.starting_category)
        await pages.start()


class AluHelpCog(MetaCog):
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
