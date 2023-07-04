from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NamedTuple, Optional, Sequence

import discord
from discord import app_commands
from discord.ext import commands, menus, tasks

from utils import AluContext
from utils.const import Colour, Emote
from utils.formats import human_timedelta
from utils.pages import Paginator

if TYPE_CHECKING:
    from utils import AluBot


class HelpFormatData(NamedTuple):
    cog: commands.Cog | Literal['front_page', 'back_page']
    cmds: Optional[Sequence[commands.Command]]


class HelpPageSource(menus.ListPageSource):
    def __init__(self, data: list[HelpFormatData], help_cmd: MyHelpCommand):
        super().__init__(entries=data, per_page=1)
        self.help_cmd: MyHelpCommand = help_cmd
        self.data: list[HelpFormatData] = data

    async def format_page(self, menu: HelpPages, entries: HelpFormatData):
        cog, cmds = entries.cog, entries.cmds

        e = discord.Embed(colour=Colour.prpl())
        e.set_footer(text=f'With love, {self.help_cmd.context.bot.user.name}')

        if cog == 'front_page':
            e.title = f'{menu.ctx_ntr.client.user.name}\'s $help Menu'
            e.description = (
                f'{menu.ctx_ntr.client.user.name} is an ultimate multi-purpose bot !\n\n'
                'Use dropdown menu below to select a category.'
            )
            e.add_field(name=f'{menu.ctx_ntr.client.owner.name}\'s server', value='[Link](https://discord.gg/K8FuDeP)')
            e.add_field(name='GitHub', value='[Link](https://github.com/Aluerie/AluBot)')
            e.add_field(name='Bot Owner', value=f'{menu.ctx_ntr.client.owner}')
        elif cog == 'back_page':
            e.title = 'Other features $help page'
            e.description = (
                f'{Emote.PepoDetective} There is a list of not listed on other pages features. '
                f'Maybe I even forgot something to write down'
            )
        elif cmds:
            e.title = getattr(cog, "qualified_name", "No Category")
            cog_desc = getattr(cog, "description", "No Description")
            cog_emote = getattr(cog, "help_emote", None)

            command_signatures = [chr(10).join(await self.help_cmd.get_the_answer(c)) for c in cmds]

            e.description = (
                f'{str(cog_emote) + " " if cog_emote else ""}{cog_desc}\n\n' f'{chr(10).join(command_signatures)}'
            )

        return e


class HelpSelect(discord.ui.Select):
    def __init__(self, paginator: HelpPages):
        super().__init__(placeholder='Choose help category')
        self.paginator: HelpPages = paginator
        self.__fill_options()

    def __fill_options(self) -> None:
        self.add_option(
            label='Home Page',
            description='Index Page of the $help menu',
            emoji='\N{HOUSE BUILDING}',
            value=str(0),
        )
        max_len = len(self.paginator.source.data)
        counter = 0
        for entry in self.paginator.source.data:
            cog = entry.cog
            if cog in ['front_page', 'back_page']:
                continue

            cog_name = getattr(cog, "qualified_name", "No Category")
            cog_desc = getattr(cog, "description", "No Description")
            cog_emote = getattr(cog, "help_emote", None)

            self.add_option(
                label=cog_name, description=cog_desc.split('\n', 1)[0], emoji=cog_emote, value=str(counter + 1)
            )
            counter += 1
        self.add_option(
            label='Other Features',
            description='Things that bot does without commands',
            emoji=Emote.PepoDetective,
            value=str(max_len - 1),
        )

    async def callback(self, ntr: discord.Interaction):
        await self.paginator.show_page(ntr, int(self.values[0]))


class HelpPages(Paginator):
    source: HelpPageSource

    def __init__(self, ctx: AluContext, source: HelpPageSource):
        super().__init__(ctx, source)
        self.add_item(HelpSelect(self))


class MyHelpCommand(commands.HelpCommand):
    context: AluContext

    def __init__(self):
        super().__init__(
            verify_checks=True,
            command_attrs={
                'hidden': False,  # change to True to hide from help menu
                'help': 'Show `help` menu for common bot commands. '
                'Note that you can use `$help [command/group/cog]` to get a help on specific things',
                'brief': f'{Emote.slash}',
            },
        )

    async def get_the_answer(self, c, answer=None, deep=0):
        if answer is None:
            answer = []
        if getattr(c, 'commands', None) is not None:
            if c.brief == Emote.slash:
                answer.append(self.get_command_signature(c))
            for x in await self.filter_commands(c.commands, sort=True):
                await self.get_the_answer(x, answer=answer, deep=deep + 1)
            if deep > 0:
                answer.append('')
        else:
            answer.append(self.get_command_signature(c))
        return answer

    def get_command_signature(self, c: commands.Command):
        def signature():
            sign = f' `{c.signature}`' if c.signature else ''
            name = c.name if not getattr(c, 'root_parent') else c.root_parent.name  # type:ignore
            app_command = self.context.bot.tree.get_app_command(name)
            if app_command:
                cmd_mention = f"</{c.qualified_name}:{app_command.id}>"
            else:
                prefix = getattr(self.context, 'clean_prefix', '$')
                cmd_mention = f'`{prefix}{c.qualified_name}`'
            return f'{cmd_mention}{sign}'

        def aliases():
            if len(c.aliases):
                return ' | aliases: ' + '; '.join([f'`{ali}`' for ali in c.aliases])
            return ''

        def cd():
            if c.cooldown is not None:
                return f' | cd: {c.cooldown.rate} per {human_timedelta(c.cooldown.per, strip=True, suffix=False)}'
            return ''

        def check():
            if c.checks:
                res = set(getattr(i, '__doc__') or "mods only" for i in c.checks)
                res = [f"*{i}*" for i in res]
                return f"**!** {', '.join(res)}\n"
            return ''

        def help_str():
            return c.help or 'No documentation'

        return f'\N{BLACK CIRCLE} {signature()}{aliases()}{cd()}\n{check()}{help_str()}'

    async def send_bot_help(self, mapping):
        await self.context.typing()
        sorted_list_of_keys = sorted(mapping, key=lambda x: getattr(x, "qualified_name", "No Category"))
        sorted_mapping = {k: mapping[k] for k in sorted_list_of_keys}

        help_data: list[HelpFormatData] = [HelpFormatData(cog='front_page', cmds=None)]
        for cog, cmds in sorted_mapping.items():
            if not getattr(cog, 'setup_info', None):
                filtered = await self.filter_commands(cmds, sort=True)
                if filtered:
                    help_data.append(HelpFormatData(cog=cog, cmds=filtered))
        help_data.append(HelpFormatData(cog='back_page', cmds=None))

        pages = HelpPages(self.context, HelpPageSource(help_data, self))
        # pages.add_item(HelpSelect())
        await pages.start()

    async def send_cog_help(self, cog):
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        command_signatures = [chr(10).join(await self.get_the_answer(c)) for c in filtered]

        cog_name = getattr(cog, "qualified_name", "No Category")
        cog_desc = getattr(cog, "description", "No Description")

        e = discord.Embed(colour=Colour.prpl(), title=cog_name)
        e.description = f'{cog_desc}\n\n{chr(10).join(command_signatures)}'
        e.set_footer(text=f'With love, {self.context.bot.user.display_name}')
        e.set_thumbnail(url=self.context.bot.user.display_avatar.url)
        await self.context.reply(embed=e)

    async def send_group_help(self, group):
        filtered = await self.filter_commands(group.commands, sort=True)
        command_signatures = [chr(10).join(await self.get_the_answer(c)) for c in filtered]
        e = discord.Embed(color=Colour.prpl(), title=group.name, description=f'{chr(10).join(command_signatures)}')
        await self.context.reply(embed=e)

    async def send_command_help(self, command):
        e = discord.Embed(
            title=command.qualified_name, color=Colour.prpl(), description=self.get_command_signature(command)
        )
        await self.context.reply(embed=e)

    async def send_error_message(self, error):
        e = discord.Embed(title="Help Command Error", description=error, color=Colour.error())
        e.set_footer(
            text=(
                'Check the spelling of your desired command/category and '
                'make sure you can use them because help command '
                'does not show commands that you are not able to use'
            )
        )
        await self.context.reply(embed=e)
