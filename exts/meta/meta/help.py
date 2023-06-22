from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Dict, List, Literal, Mapping, NamedTuple, Optional, Sequence, Tuple

import discord
from discord import app_commands
from discord.ext import commands, menus

from utils import AluCog, AluContext, ExtCategory, aluloop, const, pagination
from utils.formats import human_timedelta

from .._category import MetaCog

if TYPE_CHECKING:
    from utils import AluBot


class CogPage:
    def __init__(
        self,
        cog: Literal['_front_page'] | AluCog | commands.Cog,  # dirty way to handle front page
        cmds: Sequence[commands.Command],
        category: ExtCategory,
        page_num: int = 0,  # page per cog so mostly 0
        category_page: int = 0,
        category_len: int = 1,
    ):
        self.cog: Literal['_front_page'] | AluCog | commands.Cog = cog
        self.cmds: Sequence[commands.Command] = cmds
        self.page_num: int = page_num  # page per cog so mostly 0
        self.category_page: int = category_page
        self.category_len: int = category_len
        self.category: ExtCategory = category


class HelpPageSource(menus.ListPageSource):
    def __init__(self, data: Dict[ExtCategory, List[CogPage]]):
        entries = list(itertools.chain.from_iterable(data.values()))
        super().__init__(entries=entries, per_page=1)

    async def format_page(self, menu: HelpPages, page: CogPage):
        e = discord.Embed(colour=const.Colour.prpl())
        e.set_footer(text=f'With love, {menu.help_cmd.context.bot.user.display_name}')

        if page.cog == '_front_page':
            bot = menu.ctx_ntr.client
            e.title = f'{bot.user.name}\'s Help Menu'
            e.description = (
                f'{bot.user.name} is an ultimate multi-purpose bot !\n\n'
                'Use dropdown menu below to select a category.'
            )
            e.add_field(name=f'{bot.owner.name}\'s server', value='[Link](https://discord.gg/K8FuDeP)')
            e.add_field(name='GitHub', value='[Link](https://github.com/Aluerie/AluBot)')
            e.add_field(name='Bot Owner', value=f'@{bot.owner}')
            e.set_thumbnail(url=bot.user.display_avatar)
            return e

        e.title = page.cog.qualified_name
        emote_url = discord.PartialEmoji.from_str(page.category.emote)
        e.set_author(
            name=f'Category: {page.category.name} (page {page.category_page + 1}/{page.category_len})',
            icon_url=emote_url.url,
        )
        desc = page.cog.description + '\n\n'
        desc += chr(10).join(['\n'.join(await menu.help_cmd.get_the_answer(c)) for c in page.cmds])
        e.description = desc[:4000]  # idk #TODO: this is bad
        return e


class HelpSelect(discord.ui.Select):
    def __init__(self, paginator: HelpPages):
        super().__init__(placeholder='Choose help category')
        self.paginator: HelpPages = paginator

        self.__fill_options()

    def __fill_options(self) -> None:
        pages_per_category: Mapping[ExtCategory, Tuple[int, int]] = {}
        total = 1
        for category, cog_pages in self.paginator.help_data.items():
            starting = total
            total += len(cog_pages)
            pages_per_category[category] = starting, total - 1

        for category, (start, end) in pages_per_category.items():
            pages_string = f'(page {start})' if start == end else f'(pages {start}-{end})'
            self.add_option(
                label=f'{category.name} {pages_string}',
                emoji=category.emote,
                description=category.description,
                value=str(start - 1),  # we added 1 in total=1
            )

    async def callback(self, ntr: discord.Interaction[AluBot]):
        page_to_open = int(self.values[0])
        await self.paginator.show_page(ntr, page_to_open)


class HelpPages(pagination.Paginator):
    source: HelpPageSource

    def __init__(
        self,
        ctx: AluContext | discord.Interaction[AluBot],
        help_cmd: AluHelp,
        help_data: Dict[ExtCategory, List[CogPage]],
    ):
        self.help_cmd: AluHelp = help_cmd
        self.help_data: Dict[ExtCategory, List[CogPage]] = help_data
        super().__init__(ctx, HelpPageSource(help_data))

        self.add_item(HelpSelect(self))


class AluHelp(commands.HelpCommand):
    context: AluContext

    # todo: idk
    def __init__(self, show_hidden: bool = False) -> None:
        super().__init__(
            show_hidden=show_hidden,
            verify_checks=False,  # TODO: idk we need to decide this
            command_attrs={
                'hidden': False,
                'help': 'Show `help` menu for the bot.',
                'usage': '[command/section]',
            },
        )

    async def get_the_answer(self, c, answer=None, deep=0):
        if answer is None:
            answer = []
        if getattr(c, 'commands', None) is not None:
            if c.brief == const.Emote.slash:
                answer.append(self.get_command_signature(c))
            for x in await self.filter_commands(c.commands, sort=True):
                await self.get_the_answer(x, answer=answer, deep=deep + 1)
            if deep > 0:
                answer.append('')
        else:
            answer.append(self.get_command_signature(c))
        return answer

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

    def get_bot_mapping(self) -> Dict[ExtCategory, Dict[AluCog | commands.Cog, List[commands.Command]]]:
        """Retrieves the bot mapping passed to :meth:`send_bot_help`."""

        # TODO: include solo slash commands and Context Menu commands.
        categories = self.context.bot.category_cogs

        mapping = {category: {cog: cog.get_commands() for cog in cog_list} for category, cog_list in categories.items()}
        # todo: think how to sort front page to front
        return mapping

    async def send_bot_help(
        self,
        mapping: Dict[ExtCategory, Dict[AluCog | commands.Cog, List[commands.Command]]],
    ):
        await self.context.typing()

        index_category = ExtCategory(name='Index page', emote='\N{SWAN}', description='Index page')
        index_pages = [CogPage(cog='_front_page', cmds=[], page_num=0, category=index_category)]
        help_data: Dict[ExtCategory, List[CogPage]] = {index_category: index_pages}

        for category, cog_cmd_dict in mapping.items():
            for cog, cmds in cog_cmd_dict.items():
                filtered = await self.filter_commands(cmds, sort=True)
                if filtered:
                    page = CogPage(
                        cog=cog,
                        cmds=filtered,
                        page_num=0,
                        category=category,
                    )
                    help_data.setdefault(category, []).append(page)

        for category, cog_pages in help_data.items():
            cog_len = len(cog_pages)
            for counter, page in enumerate(cog_pages):
                page.category_len = cog_len
                page.category_page = counter

        pages = HelpPages(self.context, self, help_data)
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

    @commands.is_owner()
    @commands.command(hidden=True)
    async def devhelp(self, ctx: AluContext, *, command: Optional[str]):
        my_help = AluHelp()
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
