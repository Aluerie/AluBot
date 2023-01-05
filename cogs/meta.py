from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Literal

import unicodedata

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .utils import pages
from .utils.checks import is_owner
from .utils.context import Context
from .utils.formats import human_timedelta
from .utils.var import Cid, Clr, Ems, Rid, Lmt

if TYPE_CHECKING:
    from .utils.bot import AluBot


class DropdownHelp(discord.ui.Select):
    def __init__(self, paginator, options):
        super().__init__(placeholder='Choose help category', min_values=1, max_values=1, options=options)
        self.paginator = paginator

    async def callback(self, ntr: discord.Interaction):
        await self.paginator.goto_page(page_number=int(self.values[0]), ntr=ntr)


class ViewHelp(discord.ui.View):
    def __init__(self, paginator, options):
        super().__init__()
        self.paginator = paginator
        self.add_item(DropdownHelp(paginator, options=options))


def front_embed(ctx: Context):
    e = discord.Embed(title=f'{ctx.bot.user.name}\'s $help Menu')
    e.description = (
        f'{ctx.bot.user.name} is an ultimate multi-purpose bot !\n\n'
        'Use dropdown menu below to select a category.'
    )
    e.add_field(name=f'{ctx.bot.owner.name}\'s server', value='[Link](https://discord.gg/K8FuDeP)')
    e.add_field(name='GitHub', value='[Link](https://github.com/Aluerie/AluBot)')
    e.add_field(name='Bot Owner', value=f'{ctx.bot.owner}')
    return e


last_embed = discord.Embed(
    title='Other features $help page',
    description=(
        f'{Ems.PepoDetective} There is a list of not listed on other pages features. '
        f'Maybe I even forgot something to write down'
    ),
).add_field(
    name='• Notifications about fav Aluerie\'s streamers picking her fav champs/heroes', inline=False,
    value=f'Just look into <#{Cid.alubot}> !'
).add_field(
    name='• News feeds', inline=False,
    value=(
        f'Dota/League related news feed in <#{Cid.dota_news}> and <#{Cid.lol_news}> '
        f'taken from all over the internet! Even more, bot automatically parsed and analyses dota updates ;'
    )
).add_field(
    name='• Context Menu Commands', inline=False,
    value='Right click any user/message and find some commands in `Apps` folder'
).add_field(
    name='• Confessions', inline=False,
    value=(
        f'Just visit <#{Cid.confessions}> and use buttons at the very bottom of the channel. '
        f'There are two buttons: for anonymous and non-anonymous confessions. '
        f'If you use the latter - your server nickname will be shown in confession message.'
    )
).add_field(
    name='• Some stats', inline=False,
    value='Scroll down channel list to see some stats like my local time ;'
).add_field(
    name='• Twitch.tv notifications', inline=False,
    value=(
        f'Notifications for my own stream in <#{Cid.stream_notifs}> and '
        f'<@&{Rid.live_stream}> role for live streamers-members'
    )
).add_field(
    name='• Reaction roles', inline=False,
    value=f'Take some roles in <#{Cid.roles}>'
).add_field(
    name='• Timers', inline=False,
    value=f'Bot sometimes posts daily reminders in <#{Cid.general}>'
).add_field(
    name='• Welcoming new people', inline=False,
    value=f'The bot welcomes new people in <#{Cid.welcome}>'
).add_field(
    name='• Controlling emote spam channels', inline=False,
    value=(
        f'The bots moderates <#{Cid.comfy_spam}> and <#{Cid.emote_spam}>, '
        f'also sometimes spams these channels too ;'
    )
).add_field(
    name="• Logging", inline=False,
    value=(
        'The bot logs a lot of actions like message editing, new profile pics, emote change, etc '
        'into different channels;'
    )
).add_field(
    name="• Milestone members", inline=False,
    value=(
        f'Every 50th member of this server gets fancy <@&{Rid.milestone}> role and '
        f'small congratulation text in <#{Cid.welcome}>'
    )
).add_field(
    name="• Random comfy reactions", inline=False,
    value=f"Every message has a chance to get a comfy {Ems.peepoComfy} reaction on it ;"
).add_field(
    name='• Some important things', inline=False,
    value=f'For example, the bot does not like bots in <#{Cid.general}> and weebs in <#{Cid.weebs}>'
).add_field(
    name='• Thanks to twitch subs', inline=False,
    value=(
        f"The bot thanks people who get role <@&{Rid.subs}> via discord-twitch integration "
        f"in <#{Cid.stream_notifs}>"
    )
).add_field(
    name='• Experience system', inline=False,
    value='We have our own special experience system'
).add_field(
    name='• Reputation system', inline=False,
    value='Your "thanks", "ty" messages with mentions give people reputation or you can just use `$rep` command ;'
).add_field(
    name='• Your life is...', inline=False,
    value='Just a joke !'
)


class MyHelpCommand(commands.HelpCommand):
    context: Context

    def __init__(self,):
        super().__init__(
            verify_checks=False,
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

        checks = ''
        if c.checks:
            checks = set(getattr(i, '__doc__') or "mods only" for i in c.checks)
            checks = [f"*{i}*" for i in checks]
            checks = f"**!** {', '.join(checks)}\n"

        # slash = Ems.slash if getattr(c, '__commands_is_hybrid__', False) else ''

        aliases = ''
        if len(c.aliases):
            aliases = ' | aliases: ' + '; '.join([f'`{ali}`' for ali in c.aliases])

        cd_str = ''
        if c.cooldown is not None:
            cd_str = f' | cd: {c.cooldown.rate} per {human_timedelta(c.cooldown.per, strip=True)}'

        help_str = c.help or 'No documentation'

        def get_sign(o):
            signature = '' if o.signature == '' else f' `{o.signature}`'

            if getattr(c, 'root_parent'):
                name = c.root_parent.name
            else:
                name = c.name

            app_command = self.context.bot.tree.get_app_command(name)
            if app_command:
                cmd_mention = f"</{c.qualified_name}:{app_command.id}>"
            else:
                prefix = getattr(self.context, 'clean_prefix', '$')
                cmd_mention = f'`{prefix}{o.qualified_name}`'
            return f'{cmd_mention}{signature}'

        return f'\N{BLACK CIRCLE} {get_sign(c)}{aliases}{cd_str}\n{checks}{help_str}'

    async def send_bot_help(self, mapping):
        await self.context.typing()
        embed_list = []
        drop_options = []

        embed_list.append(front_embed(self.context))
        drop_options.append(
            discord.SelectOption(
                label='Home Page',
                description='Index Page of the $help menu',
                emoji='\N{HOUSE BUILDING}',
                value=str(0),
            )
        )

        sorted_list_of_keys = sorted(mapping, key=lambda x: getattr(x, "qualified_name", "No Category"))
        sorted_mapping = {k: mapping[k] for k in sorted_list_of_keys}
        # print(sorted_mapping)
        for cog, cmds in sorted_mapping.items():
            filtered = await self.filter_commands(cmds, sort=True)
            command_signatures = [chr(10).join(await self.get_the_answer(c)) for c in filtered]

            cog_name = getattr(cog, "qualified_name", "No Category")
            cog_desc = getattr(cog, "description", "No Description")
            cog_emote = getattr(cog, "help_emote", None)

            if command_signatures:
                e = discord.Embed(title=cog_name)
                e.description = (
                    f'{str(cog_emote) + " " if cog_emote else ""}{cog_desc}\n\n'
                    f'{chr(10).join(command_signatures)}'
                )

                embed_list.append(e)
                drop_options.append(
                    discord.SelectOption(
                        label=cog_name,
                        description=cog_desc.split('\n', 1)[0],
                        emoji=cog_emote,
                        value=str(len(embed_list) - 1)
                    )
                )

        embed_list.append(last_embed)
        drop_options.append(
            discord.SelectOption(
                label='Other Features',
                description='Things that bot does without commands',
                emoji=Ems.PepoDetective,
                value=str(len(embed_list) - 1)
            )
        )

        for e in embed_list:
            e.colour = Clr.prpl
            e.set_footer(text=f'With love, {self.context.bot.user.display_name}')
            e.set_thumbnail(url=self.context.bot.user.display_avatar.url)
        paginator = pages.Paginator(
            pages=embed_list
        )
        paginator.custom_view = ViewHelp(paginator, options=drop_options)
        await paginator.send(self.context)

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

    @property
    def feedback_channel(self) -> Optional[discord.TextChannel]:
        return self.bot.get_channel(Cid.global_logs)  # type: ignore

    # **The** famous Umbra\'s sync command holy moly. `?tag usc`. Or `?tag umbra sync command`
    @is_owner()
    @commands.command(hidden=True)
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
            e.description = f'Finished updating/rebooting. Logged in as {self.bot.user.name}.'
            await self.bot.get_channel(Cid.bot_spam).send(embed=e)

    @load_help_info.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @load_help_info.error
    async def load_help_info_error(self, error: Exception):
        await self.bot.send_traceback(error, where='load_help_info')

    @commands.command(aliases=['join'])
    async def invite(self, ctx: Context):
        """Show my invite link so you can invite me.
        You can also press discord-native button "Add to Server" in my profile.
        """
        perms = discord.Permissions.all()
        # perms.read_messages = True
        url = discord.utils.oauth_url(self.bot.client_id, permissions=perms)
        e = discord.Embed(title='Invite link for the bot', url=url, description=url, color=Clr.prpl)
        e.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=e)

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

        This is a quick way to request features or bug fixes.
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
        """Shows information about a character(-s).

        Only up to a few characters tho.
        """

        def to_string(c: str) -> str:
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, None)
            name = f'`\\N{name}`' if name else 'Name not found.'
            return (
                f'`\\U{digit:>08}` | {name} | {c} \N{EM DASH} '
                f'<https://www.fileformat.info/info/unicode/char/{digit}>'
            )

        msg = chr(10).join(map(to_string, characters))
        if len(msg) > 2000:
            e = discord.Embed(description='Output too long to display.', colour=Clr.error)
            return await ctx.send(embed=e)
        await ctx.send(msg)


async def setup(bot: AluBot):
    await bot.add_cog(Meta(bot))
