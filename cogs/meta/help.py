from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Literal, NamedTuple, Sequence, List

import discord
from discord import app_commands
from discord.ext import commands, menus, tasks

from utils.context import Context
from utils.formats import human_timedelta
from utils.pagination import Paginator
from utils.var import Cid, Clr, Ems, Rid

from ._base import MetaBase

if TYPE_CHECKING:
    from utils.bot import AluBot


class HelpFormatData(NamedTuple):
    cog: commands.Cog | Literal['front_page', 'back_page']
    cmds: Optional[Sequence[commands.Command]]


class HelpPageSource(menus.ListPageSource):
    def __init__(self, data: List[HelpFormatData], help_cmd: MyHelpCommand):
        super().__init__(entries=data, per_page=1)
        self.help_cmd: MyHelpCommand = help_cmd
        self.data: List[HelpFormatData] = data

    async def format_page(self, menu: HelpPages, entries: HelpFormatData):
        cog, cmds = entries.cog, entries.cmds

        e = discord.Embed(colour=Clr.prpl)
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
                f'{Ems.PepoDetective} There is a list of not listed on other pages features. '
                f'Maybe I even forgot something to write down'
            )
            e.add_field(
                name='• Notifications about fav Aluerie\'s streamers picking her fav champs/heroes',
                inline=False,
                value=f'Just look into <#{Cid.alubot}> !',
            )
            e.add_field(
                name='• News feeds',
                inline=False,
                value=(
                    f'Dota/League related news feed in <#{Cid.dota_news}> and <#{Cid.lol_news}> '
                    f'taken from all over the internet! Even more, bot automatically parsed and analyses dota updates ;'
                ),
            )
            e.add_field(
                name='• Context Menu Commands',
                inline=False,
                value='Right click any user/message and find some commands in `Apps` folder',
            )
            e.add_field(
                name='• Confessions',
                inline=False,
                value=(
                    f'Just visit <#{Cid.confessions}> and use buttons at the very bottom of the channel. '
                    f'There are two buttons: for anonymous and non-anonymous confessions. '
                    f'If you use the latter - your server nickname will be shown in confession message.'
                ),
            )
            e.add_field(
                name='• Some stats',
                inline=False,
                value='Scroll down channel list to see some stats like my local time ;',
            )
            e.add_field(
                name='• Twitch.tv notifications',
                inline=False,
                value=(
                    f'Notifications for my own stream in <#{Cid.stream_notifs}> and '
                    f'<@&{Rid.live_stream}> role for live streamers-members'
                ),
            )
            e.add_field(name='• Reaction roles', inline=False, value=f'Take some roles in <#{Cid.roles}>')
            e.add_field(name='• Timers', inline=False, value=f'Bot sometimes posts daily reminders in <#{Cid.general}>')
            e.add_field(
                name='• Welcoming new people', inline=False, value=f'The bot welcomes new people in <#{Cid.welcome}>'
            )
            e.add_field(
                name='• Controlling emote spam channels',
                inline=False,
                value=(
                    f'The bots moderates <#{Cid.comfy_spam}> and <#{Cid.emote_spam}>, '
                    f'also sometimes spams these channels too ;'
                ),
            )
            e.add_field(
                name="• Logging",
                inline=False,
                value=(
                    'The bot logs a lot of actions like message editing, new profile pics, emote change, etc '
                    'into different channels;'
                ),
            )
            e.add_field(
                name="• Milestone members",
                inline=False,
                value=(
                    f'Every 50th member of this server gets fancy <@&{Rid.milestone}> role and '
                    f'small congratulation text in <#{Cid.welcome}>'
                ),
            )
            e.add_field(
                name="• Random comfy reactions",
                inline=False,
                value=f"Every message has a chance to get a comfy {Ems.peepoComfy} reaction on it ;",
            )
            e.add_field(
                name='• Some important things',
                inline=False,
                value=f'For example, the bot does not like bots in <#{Cid.general}> and weebs in <#{Cid.weebs}>',
            )
            e.add_field(
                name='• Thanks to twitch subs',
                inline=False,
                value=(
                    f"The bot thanks people who get role <@&{Rid.subs}> via discord-twitch integration "
                    f"in <#{Cid.stream_notifs}>"
                ),
            )
            e.add_field(name='• Experience system', inline=False, value='We have our own special experience system')
            e.add_field(
                name='• Reputation system',
                inline=False,
                value=(
                    'Your "thanks", "ty" messages with mentions give people reputation or '
                    'you can just use `$rep` command'
                ),
            )
            e.add_field(name='• Your life is...', inline=False, value='Just a joke !')
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
            emoji=Ems.PepoDetective,
            value=str(max_len - 1),
        )

    async def callback(self, ntr: discord.Interaction):
        await self.paginator.show_page(ntr, int(self.values[0]))


class HelpPages(Paginator):
    source: HelpPageSource

    def __init__(self, ctx: Context, source: HelpPageSource):
        super().__init__(ctx, source)
        self.add_item(HelpSelect(self))


class MyHelpCommand(commands.HelpCommand):
    context: Context

    def __init__(
        self,
    ):
        super().__init__(
            verify_checks=True,
            command_attrs={
                'hidden': False,  # change to True to hide from help menu
                'help': 'Show `help` menu for common bot commands. '
                'Note that you can use `$help [command/group/cog]` to get a help on specific things',
                'brief': f'{Ems.slash}',
            },
        )

    async def get_the_answer(self, c, answer=None, deep=0):
        if answer is None:
            answer = []
        if getattr(c, 'commands', None) is not None:
            if c.brief == Ems.slash:
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
            name = c.name if not getattr(c, 'root_parent') else c.root_parent.name
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

        help_data: List[HelpFormatData] = [HelpFormatData(cog='front_page', cmds=None)]
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

        e = discord.Embed(colour=Clr.prpl, title=cog_name)
        e.description = f'{cog_desc}\n\n{chr(10).join(command_signatures)}'
        e.set_footer(text=f'With love, {self.context.bot.user.display_name}')
        e.set_thumbnail(url=self.context.bot.user.display_avatar.url)
        await self.context.reply(embed=e)

    async def send_group_help(self, group):
        filtered = await self.filter_commands(group.commands, sort=True)
        command_signatures = [chr(10).join(await self.get_the_answer(c)) for c in filtered]
        e = discord.Embed(color=Clr.prpl, title=group.name, description=f'{chr(10).join(command_signatures)}')
        await self.context.reply(embed=e)

    async def send_command_help(self, command):
        e = discord.Embed(title=command.qualified_name, color=Clr.prpl, description=self.get_command_signature(command))
        await self.context.reply(embed=e)

    async def send_error_message(self, error):
        e = discord.Embed(title="Help Command Error", description=error, color=Clr.error)
        e.set_footer(
            text=(
                'Check the spelling of your desired command/category and '
                'make sure you can use them because help command '
                'does not show commands that you are not able to use'
            )
        )
        await self.context.reply(embed=e)


class HelpCommandCog(MetaBase):
    """Commands-utilities related to Discord or the Bot itself."""

    def __init__(self, bot: AluBot):
        super().__init__(bot)
        bot.help_command = MyHelpCommand()
        bot.help_command.cog = self
        self._original_help_command: Optional[commands.HelpCommand] = bot.help_command

    async def cog_load(self) -> None:
        self.load_help_info.start()

    async def cog_unload(self) -> None:
        self.load_help_info.cancel()
        self.bot.help_command = self._original_help_command

    @app_commands.command(name='help')
    @app_commands.describe(command='Command name to get help about')
    async def help_slash(self, ntr: discord.Interaction, *, command: Optional[str]):
        """Show help menu for the bot"""
        my_help = MyHelpCommand()
        my_help.context = ctx = await Context.from_interaction(ntr)
        await my_help.command_callback(ctx, command=command)

    @tasks.loop(count=1)
    async def load_help_info(self):
        # Hmm, auto-syncing is bad, but is auto-fetching bad :thinking:
        # If I ever get rate-limited here then we will think
        await self.bot.tree.fetch_commands()

        if not self.bot.test:
            # todo: move this somewhhere else
            # announce to people that we logged in
            e = discord.Embed(colour=Clr.prpl)
            e.description = f'Logged in as {self.bot.user.name}'
            await self.bot.spam_channel.send(embed=e)
            e.set_footer(text='Finished updating/rebooting')
            await self.bot.get_channel(Cid.bot_spam).send(embed=e)

    @load_help_info.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @load_help_info.error
    async def load_help_info_error(self, error):
        await self.bot.send_traceback(error, where='load_help_info')
