from discord import ButtonStyle, Embed, Interaction, app_commands
from discord.ext import commands
from discord.ui import View, button
from utils.var import Clr, Ems, Cid, Rid, cmntn, rmntn
from utils.elpcmd import HelpCommand


def first_page(ctx):
    embed = Embed(color=Clr.prpl, title=f'{ctx.bot.user.display_name} | $help Menu')
    embed.description = f'🏠 {ctx.bot.user.display_name} is an ultimate multi-purpose bot !'
    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)
    embed.set_footer(text=f'With love, {ctx.bot.user.display_name}')
    embed.add_field(name=f'{Ems.FeelsDankMan} `Fun`', inline=False,
                    value='Commands to have fun with ;')
    embed.add_field(name=f'{Ems.DankFix} `Tools`', inline=False,
                    value='Commands providing useful tools')
    embed.add_field(name=f'{Ems.PepoG} `Info`', inline=False,
                    value='Commands to get some useful info')
    embed.add_field(name=f'{Ems.Smartge} `Stats`', inline=False,
                    value='Commands to get some stats/infographics')
    embed.add_field(name='📝 `Reminders and ToDo list`', inline=False,
                    value='Commands to organize yourself a little bit')
    embed.add_field(name=f'{Ems.peepoHappyDank} `Birthday`', inline=False,
                    value='Set your birthday and get congratulations from the bot')
    embed.add_field(name=f'{Ems.bubuAyaya} `Profile`', inline=False,
                    value='Commands about member profile')
    embed.add_field(name=f'{Ems.TwoBButt} `Irene`', inline=False,
                    value='Commands about Irene')
    embed.add_field(name=f'{Ems.PepoDetective} `Other features`', inline=False,
                    value='Things that the bot does too')
    return embed


def features_page(ctx):
    embed = Embed(color=Clr.prpl, title='Other features $help page')
    embed.description = f'{Ems.PepoDetective} There is a list of not listed on other pages features. ' \
                        f'Maybe I even forgot something to write down'
    embed.set_footer(text=f'With love, {ctx.bot.user.display_name}')
    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

    embed.add_field(name='• Notifications about fav Irene\'s streamers picking her fav champs/heroes', inline=False,
                    value=f'Just look into {cmntn(Cid.irene_bot)} !')
    embed.add_field(name='• News feeds', inline=False,
                    value=f'Dota/League related news feed in {cmntn(Cid.dota_news)} and {cmntn(Cid.lol_news)} '
                          f'taken from all over the internet! '
                          f'Even more, bot automatically parsed and analyses dota updates ;')
    embed.add_field(name='• Context Menu Commands', inline=False,
                    value='Right click any user/message and find some commands in `Apps` folder')
    embed.add_field(name='• Confessions', inline=False,
                    value=f'Just visit {cmntn(Cid.confessions)} and use buttons at the very bottom of the channel. '
                          f'There are two buttons: for anonymous and non-anonymous confessions. '
                          f'If you use the latter - your server nickname will be shown in confession message.')
    embed.add_field(name='• Some stats', inline=False,
                    value='Scroll down channel list to see some stats like my local time ;')
    embed.add_field(name='• Twitch.tv notifications', inline=False,
                    value=f'Notifications for my own stream in {cmntn(Cid.stream_notifs)} and '
                          f'{rmntn(Rid.live_stream)} role for live streamers-members ;')
    embed.add_field(name='• Reaction roles', inline=False,
                    value=f'Take some roles in {cmntn(Cid.roles)} ;')
    embed.add_field(name='• Timers', inline=False,
                    value=f'Bot sometimes posts daily reminders in {cmntn(Cid.general)} ;')
    embed.add_field(name='• Welcoming new people', inline=False,
                    value=f'The bot welcomes new people in {cmntn(Cid.welcome)} ;')
    embed.add_field(name='• Controlling emote spam channels', inline=False,
                    value=f'The bots moderates {cmntn(Cid.comfy_spam)} and {cmntn(Cid.emote_spam)}, '
                          f'also sometimes spams these channels too ;')
    embed.add_field(name="• Logging", inline=False,
                    value='The bot logs a lot of actions like message editing, new profile pics, emote change, etc '
                          'into different channels;')
    embed.add_field(name="• Milestone members", inline=False,
                    value=f'Every 50th member of this server gets fancy {rmntn(Rid.milestone)} role and '
                          f'small congratulation text in {cmntn(Cid.welcome)} ;')
    embed.add_field(name="• Random comfy reactions", inline=False,
                    value=f"Every message has a chance to get a comfy {Ems.peepoComfy} reaction on it ;")
    embed.add_field(name='• Some important things', inline=False,
                    value=f'For example, the bot doesn\'t like bots in {cmntn(Cid.general)} and '
                          f'weebs in {cmntn(Cid.weebs)} ;')
    embed.add_field(name='• Thanks to twitch subs', inline=False,
                    value=f"The bot thanks people who get role {rmntn(Rid.subs)} via discord-twitch integration "
                          f"in {cmntn(Cid.stream_notifs)} ;")
    embed.add_field(name='• Experience system', inline=False,
                    value='We have our own special experience system ;')
    embed.add_field(name='• Reputation system', inline=False,
                    value='Your "thanks", "ty" messages with mentions give people reputation or '
                          'you can just use `$rep` command ;')
    embed.add_field(name='• Your life is...', inline=False,
                    value='Just a joke !')
    return embed


class ViewHelp(View):
    def __init__(self, paginator):
        super().__init__()
        self.paginator = paginator

    @button(label="", style=ButtonStyle.primary, emoji='🏠')
    async def button0(self, ntr, btn):
        await self.paginator.goto_page(page_number=0, ntr=ntr)

    @button(label="", style=ButtonStyle.primary, emoji=Ems.FeelsDankMan)
    async def button3(self, ntr, btn):
        await self.paginator.goto_page(page_number=1, ntr=ntr)

    @button(label="", style=ButtonStyle.primary, emoji=Ems.DankFix)
    async def button4(self, ntr, btn):
        await self.paginator.goto_page(page_number=2, ntr=ntr)

    @button(label="", style=ButtonStyle.primary, emoji=Ems.PepoG)
    async def button2(self, ntr, btn):
        await self.paginator.goto_page(page_number=3, ntr=ntr)

    @button(label="", style=ButtonStyle.primary, emoji=Ems.Smartge)
    async def button1(self, ntr, btn):
        await self.paginator.goto_page(page_number=4, ntr=ntr)

    @button(label="", style=ButtonStyle.primary, emoji='📝')
    async def button5(self, ntr, btn):
        await self.paginator.goto_page(page_number=5, ntr=ntr)

    @button(label="", style=ButtonStyle.primary, emoji=Ems.peepoHappyDank)
    async def button6(self, ntr, btn):
        await self.paginator.goto_page(page_number=6, ntr=ntr)

    @button(label="", style=ButtonStyle.primary, emoji=Ems.bubuAyaya)
    async def button7(self, ntr, btn):
        await self.paginator.goto_page(page_number=7, ntr=ntr)

    @button(label="", style=ButtonStyle.primary, emoji=Ems.TwoBButt)
    async def button8(self, ntr, btn):
        await self.paginator.goto_page(page_number=8, ntr=ntr)

    @button(label="", style=ButtonStyle.primary, emoji=Ems.PepoDetective)
    async def button9(self, ntr, btn):
        await self.paginator.goto_page(page_number=9, ntr=ntr)


def get_starting_embed(ctx):
    footer_text = f'With love, {ctx.bot.user.display_name}'
    thumb_url = ctx.bot.user.display_avatar.url
    embed_dict = {
        '🏠': first_page(ctx),
        'Fun':
            Embed(
                color=Clr.prpl, title="Fun commands",
                description=f'{Ems.FeelsDankMan} Commands to have some fun with',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'Tools':
            Embed(
                color=Clr.prpl, title="Tools commands",
                description=f'{Ems.DankFix} Commands providing useful tools',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'Info':
            Embed(
                color=Clr.prpl, title="Info commands",
                description=f'{Ems.PepoG} Commands to get some useful info',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'Stats':
            Embed(
                color=Clr.prpl, title="Stats commands",
                description=f'{Ems.Smartge} Commands to get some stats/infographics',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'Todo':
            Embed(
                color=Clr.prpl, title="Reminders and ToDo list commands",
                description=f'📝 Organize yourself with some reminders and todo lists!',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'Birthday':
            Embed(
                color=Clr.prpl, title="Birthday role related commands",
                description=f'{Ems.peepoHappyDank} There is a special {rmntn(Rid.bday)} role in this server '
                            f'which on your birthday gives you a priority in the members list and makes the bot '
                            f'congratulate you. This page covers commands related to this role.'
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'Profile':
            Embed(
                color=Clr.prpl, title="Profile related commands",
                description=f'{Ems.bubuAyaya} There is a profile system in this server: levelling experience, '
                            f'currency, reputation, custom profile and many other things. '
                            f'You can find here related commands.'
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'Irene':
            Embed(
                color=Clr.prpl, title="Irene related commands",
                description=f'{Ems.TwoBButt} There are some commands to see Irene\'s progress in some things.'
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'Other': features_page(ctx)
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
        myhelp.context = await commands.Context.from_interaction(ntr)
        await myhelp.command_callback(myhelp.context)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
