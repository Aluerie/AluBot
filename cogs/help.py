from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, app_commands, SelectOption
from discord.ext import commands
from discord.ui import View, Select

from utils.help import HelpCommand
from utils.var import *
from utils.context import Context

if TYPE_CHECKING:
    from discord import Interaction


help_cat_dict = {
    'Home': {
        'title': 'AluBot ❤\'s $help Menu',
        'emote': '🏠',
        'drop': 'Home page',
        'desc': 'AluBot ❤ is an ultimate multi-purpose bot !'
    },
    'Fun': {
        'title': 'Fun',
        'emote': Ems.FeelsDankMan,
        'drop': 'Commands to have fun with',
        'desc': 'Commands to have fun with'
    },
    'Tools': {
        'title': 'Tools',
        'emote': Ems.DankFix,
        'drop': 'Commands providing useful tools',
        'desc': 'Commands providing useful tools'
    },
    'Info': {
        'title': 'Info',
        'emote': Ems.PepoG,
        'drop': 'Commands to get some useful info',
        'desc': 'Commands to get some useful info',
    },
    'Stats': {
        'title': 'Stats',
        'emote': Ems.Smartge,
        'drop': 'Commands to get some stats/infographics',
        'desc': 'Commands to get some stats/infographics',
    },
    'Lewd': {
        'title': 'Lewd',
        'emote': Ems.peepoPlsStepOnMe,
        'drop': 'NSFW tier commands',
        'desc': 'NSFW tier commands',
    },
    'Todo': {
        'title': 'Reminders and ToDo list commands',
        'emote': '📝',
        'drop': 'Organize yourself with some reminders and todo lists',
        'desc': 'Organize yourself with some reminders and todo lists',
    },
    'Birthday': {
        'title': 'Birthday',
        'emote': Ems.peepoHappyDank,
        'drop': 'Set your birthday and get congratulations from the bot',
        'desc': f'There is a special {rmntn(Rid.bday)} role in Irene\'s server '
                f'which on your birthday gives you a priority in the members list and makes the bot '
                f'congratulate you. This page covers commands related to this role.',
    },
    'Profile': {
        'title': 'Profile',
        'emote': Ems.bubuAyaya,
        'drop': 'Commands about member profiles',
        'desc': f'There is a profile system in Irene\'s server: levelling experience, '
                f'currency, reputation, custom profile and many other things. ',
    },
    'Aluerie': {
        'title': 'Aluerie',
        'emote': Ems.TwoBButt,
        'drop': 'Commands to stalk Irene\'s progress in some things',
        'desc': f'There are some commands to see Aluerie\'s info such as dota 2 match history'
    },
    'Dota 2': {
        'title': 'Dota 2',
        'emote': Ems.DankLove,
        'drop': 'Commands to set up fav hero fav stream notifs',
        'desc': 'If you want to be notified when your fav streamer picks your fav hero use these commands'
    },
    'LoL': {
        'title': 'LoL',
        'emote': Ems.PogChampPepe,
        'drop': 'Commands to set up fav hero fav stream notifs',
        'desc': 'If you want to be notified when your fav streamer picks your fav champ use these commands'
    },
    'Mute': {
        'title': 'Mute',
        'emote': Ems.peepoPolice,
        'drop': 'Commands to moderate server with',
        'desc': 'Commands to moderate server with'
    },
    'Rules': {
        'title': 'Rules',
        'emote': Ems.peepoWTF,
        'drop': 'Commands to edit rules with',
        'desc': 'Commands to edit rules with'
    },
    'AdminInfo': {
        'title': 'AdminInfo',
        'emote': Ems.peepoComfy,
        'drop': 'Commands for admin info',
        'desc': 'Commands for admin info'
    },
    'AdminTools': {
        'title': 'AdminTools',
        'emote': Ems.MadgeThreat,
        'drop': 'Commands for admin tools',
        'desc': 'Commands for admin tools'
    },
    'Other': {
        'title': 'Other features',
        'emote': Ems.PepoDetective,
        'drop': 'Features that bot does without commands',
        'desc': f'Things that the bot does too',
        'embed': Embed(
            color=Clr.prpl,
            title='Other features $help page',
            description=
            f'{Ems.PepoDetective} There is a list of not listed on other pages features. '
            f'Maybe I even forgot something to write down',
        ).add_field(
            name='• Notifications about fav Aluerie\'s streamers picking her fav champs/heroes', inline=False,
            value=f'Just look into {cmntn(Cid.alubot)} !'
        ).add_field(
            name='• News feeds', inline=False,
            value=
            f'Dota/League related news feed in {cmntn(Cid.dota_news)} and {cmntn(Cid.lol_news)} '
            f'taken from all over the internet! Even more, bot automatically parsed and analyses dota updates ;'
        ).add_field(
            name='• Context Menu Commands', inline=False,
            value='Right click any user/message and find some commands in `Apps` folder'
        ).add_field(
            name='• Confessions', inline=False,
            value=
            f'Just visit {cmntn(Cid.confessions)} and use buttons at the very bottom of the channel. '
            f'There are two buttons: for anonymous and non-anonymous confessions. '
            f'If you use the latter - your server nickname will be shown in confession message.'
        ).add_field(
            name='• Some stats', inline=False,
            value='Scroll down channel list to see some stats like my local time ;'
        ).add_field(
            name='• Twitch.tv notifications', inline=False,
            value=
            f'Notifications for my own stream in {cmntn(Cid.stream_notifs)} and '
            f'{rmntn(Rid.live_stream)} role for live streamers-members ;'
        ).add_field(
            name='• Reaction roles', inline=False,
            value=f'Take some roles in {cmntn(Cid.roles)} ;'
        ).add_field(
            name='• Timers', inline=False,
            value=f'Bot sometimes posts daily reminders in {cmntn(Cid.general)} ;'
        ).add_field(
            name='• Welcoming new people', inline=False,
            value=f'The bot welcomes new people in {cmntn(Cid.welcome)} ;'
        ).add_field(
            name='• Controlling emote spam channels', inline=False,
            value=
            f'The bots moderates {cmntn(Cid.comfy_spam)} and {cmntn(Cid.emote_spam)}, '
            f'also sometimes spams these channels too ;'
        ).add_field(
            name="• Logging", inline=False,
            value=
            'The bot logs a lot of actions like message editing, new profile pics, emote change, etc '
            'into different channels;'
        ).add_field(
            name="• Milestone members", inline=False,
            value=
            f'Every 50th member of this server gets fancy {rmntn(Rid.milestone)} role and '
            f'small congratulation text in {cmntn(Cid.welcome)} ;'
        ).add_field(
            name="• Random comfy reactions", inline=False,
            value=f"Every message has a chance to get a comfy {Ems.peepoComfy} reaction on it ;"
        ).add_field(
            name='• Some important things', inline=False,
            value=
            f'For example, the bot doesn\'t like bots in {cmntn(Cid.general)} and '
            f'weebs in {cmntn(Cid.weebs)} ;'
        ).add_field(
            name='• Thanks to twitch subs', inline=False,
            value=
            f"The bot thanks people who get role {rmntn(Rid.subs)} via discord-twitch integration "
            f"in {cmntn(Cid.stream_notifs)} ;"
        ).add_field(
            name='• Experience system', inline=False,
            value='We have our own special experience system ;'
        ).add_field(
            name='• Reputation system', inline=False,
            value=
            'Your "thanks", "ty" messages with mentions give people reputation or you can just use `$rep` command ;'
        ).add_field(
            name='• Your life is...', inline=False,
            value='Just a joke !'
        )
    }
}


class DropdownHelp(Select):
    def __init__(self, paginator):
        options = [
            SelectOption(
                label=v['title'],
                description=v['drop'],
                emoji=v['emote'],
                value=str(i)
            ) for i, (k, v) in enumerate(help_cat_dict.items())
        ]
        super().__init__(placeholder='Choose help category', min_values=1, max_values=1, options=options)
        self.paginator = paginator

    async def callback(self, ntr: Interaction):
        await self.paginator.goto_page(page_number=int(self.values[0]), ntr=ntr)


class ViewHelp(View):
    def __init__(self, paginator):
        super().__init__()
        self.paginator = paginator
        self.add_item(DropdownHelp(paginator))


def get_starting_embed(ctx):
    embed_dict = {
        k: v.get(
            'embed',
            Embed(
                colour=Clr.prpl,
                title=v['title'],
                description=f"{v['emote']} {v['desc']}"
            )
        ).set_footer(
            text=f'With love, {ctx.bot.user.display_name}'
        ).set_thumbnail(
            url=ctx.bot.user.display_avatar.url
        ) for k, v in help_cat_dict.items()
    }
    return embed_dict


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        self.help_category = 'Info'
        self.bot = bot
        bot.help_command = HelpCommand(
            get_starting_embed,
            ViewHelp,
            command_attrs={
                'help':
                    'Show `help` menu for common bot commands. '
                    'Note that you can use `$help [command/group/cog]` to get a help on specific things',
                'brief':
                    f'{Ems.slash}'
            },
            verify_checks=False
        )
        bot.help_command.cog = self

    @app_commands.command(
        name='help',
        description='Show help menu for the bot',
    )
    async def help_slash(self, ntr: Interaction):
        myhelp = HelpCommand(
            get_starting_embed,
            ViewHelp,
            verify_checks=False
        )
        myhelp.context = await Context.from_interaction(ntr)
        await myhelp.command_callback(myhelp.context)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
