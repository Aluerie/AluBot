from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from discord import Embed, SelectOption, app_commands
from discord.ext import commands
from discord.ui import View, Select

from .utils import pages
from .utils.context import Context
from .utils.format import display_hmstime
from .utils.var import Ems, Cid, rmntn, Rid, Uid, Clr

if TYPE_CHECKING:
    from discord import Interaction
    from .utils.bot import AluBot


class DropdownHelp(Select):
    def __init__(self, paginator, options):
        super().__init__(placeholder='Choose help category', min_values=1, max_values=1, options=options)
        self.paginator = paginator

    async def callback(self, ntr: Interaction):
        await self.paginator.goto_page(page_number=int(self.values[0]), ntr=ntr)


class ViewHelp(View):
    def __init__(self, paginator, options):
        super().__init__()
        self.paginator = paginator
        self.add_item(DropdownHelp(paginator, options=options))


def front_embed(context):
    em = Embed(title='AluBot ❤\'s $help Menu')
    em.description = 'AluBot ❤ is an ultimate multi-purpose bot !\n\nUse dropdown menu below to select a category.'
    em.add_field(name='Aluerie\'s server', value='[Link](https://discord.gg/K8FuDeP)')
    em.add_field(name='GitHub', value='[Link](https://github.com/Aluerie/AluBot)')
    em.add_field(name='Bot Owner', value=f'{context.bot.get_user(Uid.alu)}')
    return em


last_embed = Embed(
    title='Other features $help page',
    description=(
        f'{Ems.PepoDetective} There is a list of not listed on other pages features. '
        f'Maybe I even forgot something to write down'
    ),
).add_field(
    name='• Notifications about fav Aluerie\'s streamers picking her fav champs/heroes', inline=False,
    value=f'Just look into {Cid.alubot.mention} !'
).add_field(
    name='• News feeds', inline=False,
    value=(
        f'Dota/League related news feed in {Cid.dota_news.mention} and {Cid.lol_news.mention} '
        f'taken from all over the internet! Even more, bot automatically parsed and analyses dota updates ;'
    )
).add_field(
    name='• Context Menu Commands', inline=False,
    value='Right click any user/message and find some commands in `Apps` folder'
).add_field(
    name='• Confessions', inline=False,
    value=(
        f'Just visit {Cid.confessions.mention} and use buttons at the very bottom of the channel. '
        f'There are two buttons: for anonymous and non-anonymous confessions. '
        f'If you use the latter - your server nickname will be shown in confession message.'
    )
).add_field(
    name='• Some stats', inline=False,
    value='Scroll down channel list to see some stats like my local time ;'
).add_field(
    name='• Twitch.tv notifications', inline=False,
    value=(
        f'Notifications for my own stream in {Cid.stream_notifs.mention} and '
        f'{rmntn(Rid.live_stream)} role for live streamers-members ;'
    )
).add_field(
    name='• Reaction roles', inline=False,
    value=f'Take some roles in {Cid.roles.mention} ;'
).add_field(
    name='• Timers', inline=False,
    value=f'Bot sometimes posts daily reminders in {Cid.general.mention} ;'
).add_field(
    name='• Welcoming new people', inline=False,
    value=f'The bot welcomes new people in {Cid.welcome.mention} ;'
).add_field(
    name='• Controlling emote spam channels', inline=False,
    value=(
        f'The bots moderates {Cid.comfy_spam.mention} and {Cid.emote_spam.mention}, '
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
        f'Every 50th member of this server gets fancy {rmntn(Rid.milestone)} role and '
        f'small congratulation text in {Cid.welcome.mention} ;'
    )
).add_field(
    name="• Random comfy reactions", inline=False,
    value=f"Every message has a chance to get a comfy {Ems.peepoComfy} reaction on it ;"
).add_field(
    name='• Some important things', inline=False,
    value=(
        f'For example, the bot doesn\'t like bots in {Cid.general.mention} and '
        f'weebs in {Cid.weebs.mention} ;'
    )
).add_field(
    name='• Thanks to twitch subs', inline=False,
    value=(
        f"The bot thanks people who get role {rmntn(Rid.subs)} via discord-twitch integration "
        f"in {Cid.stream_notifs.mention} ;"
    )
).add_field(
    name='• Experience system', inline=False,
    value='We have our own special experience system ;'
).add_field(
    name='• Reputation system', inline=False,
    value='Your "thanks", "ty" messages with mentions give people reputation or you can just use `$rep` command ;'
).add_field(
    name='• Your life is...', inline=False,
    value='Just a joke !'
)


class HelpCommand(commands.HelpCommand):
    context: Context

    """def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bot = self.context.bot"""  # context is a missing sentinel on definiton huh :c

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
            cd_str = f' | cd: {c.cooldown.rate} per {display_hmstime(c.cooldown.per)}'

        help_str = c.help or 'No documentation'

        def get_sign(o):
            signature = '' if o.signature == '' else f' `{o.signature}`'

            if getattr(c, 'root_parent'):
                name = c.root_parent.name
            else:
                name = c.name

            app_command = self.context.bot.get_app_command(name)
            if app_command:
                cmd_name, cmd_id = app_command
                cmd_mention = f"</{c.qualified_name}:{cmd_id}>"
            else:
                prefix = getattr(self.context, 'clean_prefix', '$')
                cmd_mention = f'`{prefix}{o.qualified_name}`'
            return f'{cmd_mention}{signature}'

        return f'● {get_sign(c)}{aliases}{cd_str}\n{checks}{help_str}'

    async def send_bot_help(self, mapping):
        await self.context.typing()
        await self.context.bot.update_app_commands_cache()
        embed_list = []
        drop_options = []

        embed_list.append(front_embed(self.context))
        drop_options.append(
            SelectOption(
                label='Home Page',
                description='Index Page of the $help menu',
                emoji='🏠',
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
                em = Embed(title=cog_name)
                em.description = (
                    f'{cog_emote + " " if cog_emote else ""}'
                    f'{cog_desc}\n\n'
                    f'{chr(10).join(command_signatures)}'
                )

                embed_list.append(em)
                drop_options.append(
                    SelectOption(
                        label=cog_name,
                        description=cog_desc.split('\n', 1)[0],
                        emoji=cog_emote,
                        value=str(len(embed_list) - 1)
                    )
                )

        embed_list.append(last_embed)
        drop_options.append(
            SelectOption(
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
        await self.context.bot.update_app_commands_cache()
        command_signatures = [chr(10).join(await self.get_the_answer(c)) for c in filtered]

        cog_name = getattr(cog, "qualified_name", "No Category")
        cog_desc = getattr(cog, "description", "No Description")

        em = Embed(colour=Clr.prpl, title=cog_name)
        em.description = f'{cog_desc}\n\n{chr(10).join(command_signatures)}'
        em.set_footer(text=f'With love, {self.context.bot.user.display_name}')
        em.set_thumbnail(url=self.context.bot.user.display_avatar.url)
        await self.context.reply(embed=em)

    async def send_group_help(self, group):
        filtered = await self.filter_commands(group.commands, sort=True)
        await self.context.bot.update_app_commands_cache()
        command_signatures = [chr(10).join(await self.get_the_answer(c)) for c in filtered]
        em = Embed(color=Clr.prpl, title=group.name, description=f'{chr(10).join(command_signatures)}')
        await self.context.reply(embed=em)

    async def send_command_help(self, command):
        await self.context.bot.update_app_commands_cache()
        em = Embed(title=command.qualified_name, color=Clr.prpl, description=self.get_command_signature(command))
        await self.context.reply(embed=em)

    async def send_error_message(self, error):
        em = Embed(title="Help Command Error", description=error, color=Clr.error)
        em.set_footer(
            text=(
                'Check the spelling of your desired command/category and '
                'make sure you can use them because help command '
                'does not show commands that you are not able to use'
            )
        )
        await self.context.reply(embed=em)


class HelpCog(commands.Cog, name='Help'):
    def __init__(self, bot: AluBot):
        self._original_help_command = bot.help_command
        self.bot: AluBot = bot
        bot.help_command = HelpCommand(
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

    @app_commands.command(
        name='help',
        description='Show help menu for the bot',
    )
    async def help_slash(self, ntr: Interaction, *, command: Optional[str]):
        myhelp = HelpCommand(
            verify_checks=False,
            command_attrs={
                'hidden': True
            }
        )
        myhelp.context = await Context.from_interaction(ntr)
        await myhelp.command_callback(myhelp.context, command=command)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
