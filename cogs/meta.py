from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Literal, NamedTuple, Sequence, List
from typing_extensions import Self

import unicodedata

import discord
from discord import app_commands
from discord.ext import commands, menus, tasks

from .utils import checks
from .utils.checks import is_owner
from .utils.context import Context
from .utils.formats import human_timedelta
from .utils.pagination import Paginator
from .utils.var import Cid, Clr, Ems, Rid, Lmt

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import GuildContext


# #####################################################################################################################
# HELP CLASSES ########################################################################################################
# #####################################################################################################################
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
            e.title = f'{menu.ctx_ntr.bot.user.name}\'s $help Menu'
            e.description = (
                f'{menu.ctx_ntr.bot.user.name} is an ultimate multi-purpose bot !\n\n'
                'Use dropdown menu below to select a category.'
            )
            e.add_field(name=f'{menu.ctx_ntr.bot.owner.name}\'s server', value='[Link](https://discord.gg/K8FuDeP)')
            e.add_field(name='GitHub', value='[Link](https://github.com/Aluerie/AluBot)')
            e.add_field(name='Bot Owner', value=f'{menu.ctx_ntr.bot.owner}')
        elif cog == 'back_page':
            e.title = 'Other features $help page'
            e.description = (
                f'{Ems.PepoDetective} There is a list of not listed on other pages features. '
                f'Maybe I even forgot something to write down'
            )
            e.add_field(
                name='• Notifications about fav Aluerie\'s streamers picking her fav champs/heroes', inline=False,
                value=f'Just look into <#{Cid.alubot}> !'
            )
            e.add_field(
                name='• News feeds', inline=False,
                value=(
                    f'Dota/League related news feed in <#{Cid.dota_news}> and <#{Cid.lol_news}> '
                    f'taken from all over the internet! Even more, bot automatically parsed and analyses dota updates ;'
                )
            )
            e.add_field(
                name='• Context Menu Commands', inline=False,
                value='Right click any user/message and find some commands in `Apps` folder'
            )
            e.add_field(
                name='• Confessions', inline=False,
                value=(
                    f'Just visit <#{Cid.confessions}> and use buttons at the very bottom of the channel. '
                    f'There are two buttons: for anonymous and non-anonymous confessions. '
                    f'If you use the latter - your server nickname will be shown in confession message.'
                )
            )
            e.add_field(
                name='• Some stats', inline=False,
                value='Scroll down channel list to see some stats like my local time ;'
            )
            e.add_field(
                name='• Twitch.tv notifications', inline=False,
                value=(
                    f'Notifications for my own stream in <#{Cid.stream_notifs}> and '
                    f'<@&{Rid.live_stream}> role for live streamers-members'
                )
            )
            e.add_field(
                name='• Reaction roles', inline=False,
                value=f'Take some roles in <#{Cid.roles}>'
            )
            e.add_field(
                name='• Timers', inline=False,
                value=f'Bot sometimes posts daily reminders in <#{Cid.general}>'
            )
            e.add_field(
                name='• Welcoming new people', inline=False,
                value=f'The bot welcomes new people in <#{Cid.welcome}>'
            )
            e.add_field(
                name='• Controlling emote spam channels', inline=False,
                value=(
                    f'The bots moderates <#{Cid.comfy_spam}> and <#{Cid.emote_spam}>, '
                    f'also sometimes spams these channels too ;'
                )
            )
            e.add_field(
                name="• Logging", inline=False,
                value=(
                    'The bot logs a lot of actions like message editing, new profile pics, emote change, etc '
                    'into different channels;'
                )
            )
            e.add_field(
                name="• Milestone members", inline=False,
                value=(
                    f'Every 50th member of this server gets fancy <@&{Rid.milestone}> role and '
                    f'small congratulation text in <#{Cid.welcome}>'
                )
            )
            e.add_field(
                name="• Random comfy reactions", inline=False,
                value=f"Every message has a chance to get a comfy {Ems.peepoComfy} reaction on it ;"
            )
            e.add_field(
                name='• Some important things', inline=False,
                value=f'For example, the bot does not like bots in <#{Cid.general}> and weebs in <#{Cid.weebs}>'
            )
            e.add_field(
                name='• Thanks to twitch subs', inline=False,
                value=(
                    f"The bot thanks people who get role <@&{Rid.subs}> via discord-twitch integration "
                    f"in <#{Cid.stream_notifs}>"
                )
            )
            e.add_field(
                name='• Experience system', inline=False,
                value='We have our own special experience system'
            )
            e.add_field(
                name='• Reputation system', inline=False,
                value=(
                    'Your "thanks", "ty" messages with mentions give people reputation or '
                    'you can just use `$rep` command'
                )
            )
            e.add_field(
                name='• Your life is...', inline=False,
                value='Just a joke !'
            )
        else:
            e.title = getattr(cog, "qualified_name", "No Category")
            cog_desc = getattr(cog, "description", "No Description")
            cog_emote = getattr(cog, "help_emote", None)

            command_signatures = [chr(10).join(await self.help_cmd.get_the_answer(c)) for c in cmds]

            e.description = (
                f'{str(cog_emote) + " " if cog_emote else ""}{cog_desc}\n\n'
                f'{chr(10).join(command_signatures)}'
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
                label=cog_name,
                description=cog_desc.split('\n', 1)[0],
                emoji=cog_emote,
                value=str(counter + 1)
            )
            counter += 1
        self.add_option(
            label='Other Features',
            description='Things that bot does without commands',
            emoji=Ems.PepoDetective,
            value=str(max_len - 1)
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

    def __init__(self,):
        super().__init__(
            verify_checks=True,
            command_attrs={
                'hidden': False,  # change to True to hide from help menu
                'help':
                    'Show `help` menu for common bot commands. '
                    'Note that you can use `$help [command/group/cog]` to get a help on specific things',
                'brief':
                    f'{Ems.slash}'
            }
        )

    async def get_the_answer(self, c, answer=None, deep=0):
        if answer is None:
            answer = []
        if getattr(c, 'commands', None) is not None:
            if c.brief == Ems.slash:
                answer.append(self.get_command_signature(c))
            for x in await self.filter_commands(c.commands, sort=True):
                await self.get_the_answer(x, answer=answer, deep=deep+1)
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


# #####################################################################################################################
# FEEDBACK CLASSES ####################################################################################################
# #####################################################################################################################

class FeedbackModal(discord.ui.Modal, title='Submit Feedback'):
    summary = discord.ui.TextInput(
        label='Summary',
        placeholder='A brief explanation of what you want',
        max_length=Lmt.Embed.title
    )
    details = discord.ui.TextInput(
        label='Details',
        placeholder='Leave a comment',
        style=discord.TextStyle.long,
        required=False
    )

    def __init__(self, cog: Meta) -> None:
        super().__init__()
        self.cog: Meta = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = self.cog.feedback_channel
        if channel is None:
            await interaction.response.send_message('Sorry, something went wrong \N{THINKING FACE}', ephemeral=True)
            return

        e = self.cog.get_feedback_embed(interaction, summary=str(self.summary), details=self.details.value)
        await channel.send(embed=e)
        e2 = discord.Embed(colour=Clr.prpl, description='Successfully submitted feedback')
        await interaction.response.send_message(embed=e2, ephemeral=True)


# #####################################################################################################################
# SETUP CLASSES #######################################################################################################
# #####################################################################################################################
class SetupFormatData(NamedTuple):
    cog: commands.Cog | Literal['front_page', 'back_page']


class SetupSelect(discord.ui.Select):
    def __init__(self, paginator: SetupPages):
        super().__init__(placeholder='Choose setup category')
        self.paginator: SetupPages = paginator
        self.__fill_options()

    def __fill_options(self) -> None:
        self.add_option(
            label='Home Page',
            description='Index Page of the setup menu',
            emoji='\N{HOUSE BUILDING}',
            value=str(0),
        )
        counter = 0
        for entry in self.paginator.source.data:
            cog = entry.cog
            if cog in ['front_page']:
                continue

            cog_name = getattr(cog, "qualified_name", "No Category")
            cog_desc = getattr(cog, "description", "No Description")
            cog_emote = getattr(cog, "setup_emote", None)

            self.add_option(
                label=cog_name,
                description=cog_desc,
                emoji=cog_emote,
                value=str(counter + 1)
            )
            counter += 1

    async def callback(self, ntr: discord.Interaction):
        await self.paginator.show_page(ntr, int(self.values[0]))


class SetupPageSource(menus.ListPageSource):
    def __init__(self, data: List[SetupFormatData]):
        super().__init__(entries=data, per_page=1)
        self.data: List[SetupFormatData] = data

    async def format_page(self, menu: SetupPages, entries: SetupFormatData):
        cog = entries.cog
        if cog == 'front_page':
            # todo: fill it properly
            e = discord.Embed(colour=Clr.prpl)
            e.description = 'Front page baby'
            return e
        else:
            embeds = []
            setup_info = getattr(cog, 'setup_info', None)  # method cog.setup_info(self)
            if setup_info:
                embeds.append(await setup_info())
            setup_state = getattr(cog, 'setup_state', None)  # method cog.setup_state(self, ctx: Context)
            if setup_state:
                embeds.append(await setup_state(menu.ctx_ntr))

            if v := getattr(cog, 'setup_view', None):  # method cog.setup_view(self, pages: SetupPages)
                view: discord.ui.View = await v(menu)
                menu.clear_items()
                menu.fill_items()
                menu.add_item(SetupSelect(menu))
                for c in view.children:
                    menu.add_item(c)
            return {'embeds': embeds}


class SetupPages(Paginator):
    source: SetupPageSource

    def __init__(self, ctx: Context, source: SetupPageSource):
        super().__init__(ctx, source)
        self.show_text_cmds = True
        self.add_item(SetupSelect(self))

    def update_more_labels(self, page_number: int) -> None:
        self.text_cmds.label = '\N{NOTEBOOK}' if self.show_text_cmds else '\N{OPEN BOOK}'

    def fill_items(self):
        if self.source.is_paginating():
            for item in [
                self.refresh,
                self.previous_page,
                self.index,
                self.next_page,
                self.text_cmds
            ]:
                self.add_item(item)

    @discord.ui.button(label='\N{NOTEBOOK}', style=discord.ButtonStyle.blurple)
    async def text_cmds(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        """Toggle showing text commands embed in the setup paginator"""
        self.show_text_cmds = not self.show_text_cmds
        await self.show_page(ntr, self.current_page_number)


class SetupCog:

    @property
    def setup_emote(self):
        raise NotImplementedError

    async def setup_info(self) -> discord.Embed:
        raise NotImplementedError

    async def setup_state(self, ctx: Context) -> discord.Embed:
        raise NotImplementedError

    async def setup_view(self, pages: SetupPages) -> discord.ui.View:
        raise NotImplementedError


# #####################################################################################################################
# Cog #####################################################################################################
# #####################################################################################################################


class Meta(commands.Cog):
    """Commands-utilities related to Discord or the Bot itself."""

    def __init__(self, bot: AluBot):
        bot.help_command = MyHelpCommand()
        bot.help_command.cog = self
        self.bot: AluBot = bot
        self._original_help_command: Optional[commands.HelpCommand] = bot.help_command

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.FeelsDankManLostHisHat)

    async def cog_load(self) -> None:
        self.load_help_info.start()

    async def cog_unload(self) -> None:
        self.load_help_info.cancel()
        self.bot.help_command = self._original_help_command

    @commands.hybrid_command()
    async def setup(self, ctx: Context):
        setup_data: List[SetupFormatData] = [SetupFormatData(cog='front_page')]
        for cog_name, cog in self.bot.cogs.items():
            if getattr(cog, 'setup_info', None):
                setup_data.append(SetupFormatData(cog=cog))

        pages = SetupPages(ctx, SetupPageSource(setup_data))
        await pages.start()

    # **The** famous Umbra\'s sync command holy moly. `?tag usc`. Or `?tag umbra sync command`
    @is_owner()
    @commands.command()
    async def sync(
            self,
            ctx: Context,
            guilds: commands.Greedy[discord.Object],
            spec: Optional[Literal["~", "*", "^"]] = None
    ) -> None:
        """Sync command. Usage examples:
        * `$sync` -> global sync
        * `$sync ~` -> sync current guild
        * `$sync *` -> copies all global app commands to current guild and syncs
        * `$sync ^` -> clears all commands from the current guild target and syncs (removes guild commands)
        * `$sync id_1 id_2` -> syncs guilds with id 1 and 2
        """
        if not guilds:
            match spec:
                case "~":
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                case "*":
                    ctx.bot.tree.copy_global_to(guild=ctx.guild)
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                case "^":
                    ctx.bot.tree.clear_commands(guild=ctx.guild)
                    await ctx.bot.tree.sync(guild=ctx.guild)
                    synced = []
                case _:
                    synced = await ctx.bot.tree.sync()

            e = discord.Embed(colour=Clr.prpl)
            e.description = f"Synced `{len(synced)}` commands {'globally' if spec is None else 'to the current guild.'}"
            await ctx.reply(embed=e)
            return

        fmt = 0
        cmds = []
        for guild in guilds:
            try:
                cmds += await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                fmt += 1
        e = discord.Embed(colour=Clr.prpl)
        e.description = f"Synced the tree to `{fmt}/{len(guilds)}` guilds."
        await ctx.reply(embed=e)

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

    @commands.command(aliases=['join'])
    async def invite(self, ctx: Context):
        """Show the invite link, so you can add me to your server.
        You can also press "Add to Server" button in my profile.
        """
        perms = discord.Permissions.all()
        # perms.read_messages = True
        url = discord.utils.oauth_url(self.bot.client_id, permissions=perms)
        e = discord.Embed(title='Invite link for the bot', url=url, description=url, color=Clr.prpl)
        e.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=e)

    @property
    def feedback_channel(self) -> Optional[discord.TextChannel]:
        return self.bot.get_channel(Cid.global_logs)  # type: ignore

    @staticmethod
    def get_feedback_embed(
        ctx_ntr: Context | discord.Interaction,
        *,
        summary: Optional[str] = None,
        details: Optional[str] = None,
    ) -> discord.Embed:
        e = discord.Embed(title=summary, description=details, colour=Clr.prpl)

        if ctx_ntr.guild is not None:
            e.add_field(name='Server', value=f'{ctx_ntr.guild.name} | ID: {ctx_ntr.guild.id}', inline=False)

        if ctx_ntr.channel is not None:
            e.add_field(name='Channel', value=f'#{ctx_ntr.channel} | ID: {ctx_ntr.channel.id}', inline=False)

        if isinstance(ctx_ntr, discord.Interaction):
            e.timestamp, user = ctx_ntr.created_at, ctx_ntr.user
        else:
            e.timestamp, user = ctx_ntr.message.created_at, ctx_ntr.author
        e.set_author(name=str(user), icon_url=user.display_avatar.url)
        e.set_footer(text=f'Author ID: {user.id}')
        return e

    @commands.command()
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def feedback(self, ctx: Context, *, details: str):
        """Give feedback about the bot directly to the bot developer.
        This is a quick way to request features or bug fixes. \
        The bot will DM you about the status of your request if possible/needed.
        You can also open issues/PR on [GitHub](https://github.com/Aluerie/AluBot).
        """
        channel = self.feedback_channel
        if channel is None:
            return

        e = self.get_feedback_embed(ctx, details=details)
        await channel.send(embed=e)
        e2 = discord.Embed(colour=Clr.prpl, description='Successfully sent feedback')
        await ctx.send(embed=e2)

    @app_commands.command(name='feedback')
    async def slash_feedback(self, ntr: discord.Interaction):
        """Give feedback about the bot directly to the bot developer."""
        await ntr.response.send_modal(FeedbackModal(self))

    @is_owner()
    @commands.command(aliases=['pm'], hidden=True)
    async def dm(self, ctx: Context, user: discord.User, *, content: str):
        e = discord.Embed(colour=Clr.prpl, title='Message from a developer')
        e.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        e.description = content
        e.set_footer(
            text=(
                'This message is sent to you in DMs because you had previously submitted feedback or '
                'I found a bug in a command you used, I do not monitor this DM.'
            )
        )
        await user.send(embed=e)
        e2 = discord.Embed(colour=Clr.prpl, description='DM successfully sent.')
        await ctx.send(embed=e2)

    @commands.command()
    async def charinfo(self, ctx: Context, *, characters: str):
        """Shows information about a character(-s). \
        Only up to a few characters tho.
        """

        def to_string(c: str) -> str:
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, None)
            name = f'`\\N{{{name}}}`' if name else 'Name not found.'
            return (
                f'{name} \n `\\U{digit:>08}` | {c} | '
                f'<https://www.fileformat.info/info/unicode/char/{digit}>'
            )

        msg = chr(10).join(map(to_string, characters))
        if len(msg) > 2000:
            e = discord.Embed(description='Output too long to display.', colour=Clr.error)
            return await ctx.send(embed=e)
        await ctx.send(msg)


# #####################################################################################################################
# Prefix CLASSES ######################################################################################################
# #####################################################################################################################
class PrefixSetModal(discord.ui.Modal, title='New prefix setup'):

    prefix = discord.ui.TextInput(
        label='New prefix for the server',
        placeholder='Enter up to 3 character',
        max_length=3
    )

    def __init__(self, cog: PrefixSetupCog, paginator: SetupPages) -> None:
        super().__init__()
        self.cog: PrefixSetupCog = cog
        self.paginator: SetupPages = paginator

    async def on_error(self, ntr: discord.Interaction, error: Exception, /) -> None:
        e = discord.Embed(colour=Clr.error)
        if isinstance(error, commands.BadArgument):
            e.description = f'{error}'
        else:
            e.description = 'Unknown error, sorry'
        await ntr.response.send_message(embed=e, ephemeral=True)

    async def on_submit(self, ntr: discord.Interaction[AluBot]) -> None:
        p: GuildPrefix = await GuildPrefix.construct(ntr.client, ntr.guild, str(self.prefix.value))
        e = await p.set_prefix()
        await ntr.response.send_message(embed=e, ephemeral=True)
        await self.paginator.show_page(ntr, self.paginator.current_page_number)


class PrefixSetupView(discord.ui.View):
    def __init__(self, cog: PrefixSetupCog, paginator: SetupPages) -> None:
        super().__init__()
        self.cog: PrefixSetupCog = cog
        self.paginator: SetupPages = paginator

    @discord.ui.button(emoji='\N{HEAVY DOLLAR SIGN}', label='Change prefix', style=discord.ButtonStyle.blurple)
    async def set_prefix(self, ntr: discord.Interaction[AluBot], _btn: discord.ui.Button):
        await ntr.response.send_modal(PrefixSetModal(self.cog, self.paginator))

    @discord.ui.button(emoji='\N{BANKNOTE WITH DOLLAR SIGN}', label='Reset prefix', style=discord.ButtonStyle.blurple)
    async def reset_prefix(self, ntr: discord.Interaction[AluBot], _btn: discord.ui.Button):
        p = GuildPrefix(ntr.client, ntr.guild)
        e = await p.set_prefix()
        await ntr.response.send_message(embed=e, ephemeral=True)
        await self.paginator.show_page(ntr, self.paginator.current_page_number)


class GuildPrefix:
    def __init__(self, bot: AluBot, guild: discord.Guild, prefix: Optional[str] = None):
        self.bot: AluBot = bot
        self.guild: discord.Guild = guild
        self.prefix: str = prefix if prefix else bot.main_prefix  # reset zone

    @classmethod
    async def from_guild(cls, bot: AluBot, guild: discord.Guild) -> Self:
        prefix = bot.prefixes.get(guild.id)
        if prefix is None:
            prefix = bot.main_prefix
        return cls(bot, guild, prefix)

    def check_prefix(self) -> discord.Embed:
        e = discord.Embed(colour=Clr.rspbrry)
        e.description = f'Current prefix: `{self.prefix}`'
        return e

    @classmethod
    async def construct(cls, bot: AluBot, guild: discord.Guild, new_prefix: str) -> Self:
        bot_user_id = bot.user.id
        # Since I want to allow people to set prefixes with SetupView -
        # I guess I have to do these quirks to be able to check prefix both in Interactions and from Converters
        # Eh, probably we should not restrict people much, but eh let's do it for fun logic reasons.
        # Anyway, now let's verify Prefix
        if new_prefix.startswith((f'<@{bot_user_id}>', f'<@!{bot_user_id}>')):
            # Just to remind the user that it is a thing, even tho modal doesn't allow >3 characters;
            raise commands.BadArgument('That is a reserved prefix already in use.')
        if len(new_prefix.split()) > 1:
            raise commands.BadArgument('Space usage is not allowed in `prefix set` command')
        if (le := len(new_prefix)) > 3:
            raise commands.BadArgument(f'Prefix should consist of 1, 2 or 3 characters. Not {le} !')
        return cls(bot, guild, new_prefix)

    @classmethod
    async def convert(cls, ctx: GuildContext, new_prefix: str) -> Self:
        return cls.construct(ctx.bot, ctx.guild, new_prefix)

    async def set_prefix(self) -> discord.Embed:
        guild_id, new_prefix = self.guild.id, self.prefix
        e = discord.Embed(colour=Clr.prpl)
        if self.prefix == self.bot.main_prefix:
            await self.bot.prefixes.remove(guild_id)
            e.description = f'Successfully reset prefix to our default `{new_prefix}` sign'
        else:
            await self.bot.prefixes.put(guild_id, new_prefix)
            e.description = f'Changed this server prefix to `{new_prefix}`'
        return e


class PrefixSetupCog(commands.Cog, SetupCog, name='Prefix Setup'):
    """Change the server prefix for text commands"""

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def setup_emote(self):
        return '\N{HEAVY DOLLAR SIGN}'

    async def setup_info(self):
        e = discord.Embed(colour=Clr.prpl)
        e.title = 'Server Prefix Setup'
        e.description = (
            'You can choose server prefix with button "Change prefix" below. \n\n'
            f'Bot\'s default prefix for text commands is `{self.bot.main_prefix}`.\n'
            f'The bot also always answers on @-mentions, i.e. {self.bot.user.mention}` help`.'
        )
        return e

    async def setup_state(self, ctx: GuildContext):
        p = await GuildPrefix.from_guild(self.bot, ctx.guild)
        return p.check_prefix()

    async def setup_view(self, pages: SetupPages):
        return PrefixSetupView(self, pages)

    async def prefix_prefix_check_replies(self, ctx: GuildContext):
        p = await GuildPrefix.from_guild(self.bot, ctx.guild)
        e = p.check_prefix()
        e.set_footer(text=f'To change prefix use `@{self.bot.user.name} prefix set` command')
        await ctx.reply(embed=e)

    @checks.is_manager()
    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx: GuildContext):
        """Group command about prefix for this server"""
        await self.prefix_prefix_check_replies(ctx)

    @checks.is_manager()
    @prefix.command(name='check')
    async def prefix_check(self, ctx: GuildContext):
        """Check prefix for this server"""
        await self.prefix_prefix_check_replies(ctx)

    @checks.is_manager()
    @prefix.command(name='set')
    async def prefix_set(self, ctx: GuildContext, *, new_prefix: GuildPrefix):
        """Set new prefix for the server.
        If you have troubles to set a new prefix because other bots also answer it then \
        just mention the bot with the command <@713124699663499274>` prefix set`.
        Spaces are not allowed in the prefix, and it should be 1-3 symbols.
        """
        e = new_prefix.set_prefix()
        await ctx.reply(embed=e)


async def setup(bot: AluBot):
    await bot.add_cog(Meta(bot))
    await bot.add_cog(PrefixSetupCog(bot))
