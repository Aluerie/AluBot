from discord import Embed, Interaction, SelectOption, option, ui
from discord.utils import format_dt
from discord.ext import commands, bridge

from utils.var import *

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from datetime import datetime, timezone

fav_teams = ['[A]', 'Bald', 'GS']


async def schedule_work(arg, mod, only_today=0, favmode=0):
    async with ClientSession() as session:
        async with session.get(my_url := 'https://liquipedia.net/dota2/Liquipedia:Upcoming_and_ongoing_matches') as r:
            soup = BeautifulSoup(await r.read(), 'html.parser')
    embed = Embed(colour=Clr.prpl)
    embed.set_author(name='Info from Liquipedia.net', icon_url=Img.dota2logo, url=my_url)
    embed.title = 'Dota 2 Pro Matches Schedule'
    embed.url = my_url
    dict_teams = {}
    symb_amount = 15
    dt_now = datetime.now(timezone.utc)

    def work_func(mod, part=1):
        divs = soup.findAll("div", {"data-toggle-area-content": mod})
        rows = divs[-1].findAll("tbody")
        for row in rows:
            lname = row.select_one('.team-left').text.strip().replace('`', '.')
            rname = row.select_one('.team-right').text.strip().replace('`', '.')
            time_utc = row.select_one('.match-countdown').text.strip()
            dt = datetime.strptime(time_utc, '%B %d, %Y - %H:%M UTC').replace(tzinfo=timezone.utc)
            if only_today:
                timedelta_obj = dt - dt_now
                if timedelta_obj.days > 0:
                    continue
            league = row.select_one('.match-filler').text.strip().replace(time_utc, '')

            if part == 1 and arg is not None:
                do_we_post = 0
                for item in [lname, rname, league]:
                    if arg in item:
                        do_we_post = 1
                if not do_we_post:
                    continue

            if part == 2:
                do_we_post = 0
                for item in [lname, rname]:
                    if item in fav_teams:
                        do_we_post = 1
                if not do_we_post:
                    continue

            teams = f'{lname} - {rname}'
            teams = teams[:symb_amount]
            if league not in dict_teams:
                dict_teams[league] = []
            answer = f"`{teams.ljust(symb_amount, ' ')}`{format_dt(dt, style='t')} {format_dt(dt, style='R')}"
            if answer not in dict_teams[league]:  # remove duplicates if any
                dict_teams[league].append(answer)

    work_func(mod, part=1)
    if favmode == 1:
        work_func("1", part=2)

    answer_str = f'Applied filter: `{arg}`\n' if arg is not None else ''
    answer_str += \
        f'`{"Datetime now ".ljust(symb_amount, " ")}`{format_dt(dt_now, style="t")} {format_dt(dt_now, style="d")}\n\n'
    for key in dict_teams:
        answer_str += f"**{key}**\n"
        answer_str += "\n".join(dict_teams[key])
        answer_str += "\n"
    embed.description = answer_str
    return embed


options = [
    SelectOption(
        emoji=Ems.PepoRules,
        label="Next 24h: Featured + Favourite (Default)",
        description="Featured games + some fav teams next 24 hours",
    ),
    SelectOption(
        emoji=Ems.peepoHappyDank,
        label="Next 24h: Featured",
        description="Featured games next 24 hours",
    ),
    SelectOption(
        emoji=Ems.bubuAyaya,
        label="Featured",
        description="Featured games by Liquidpedia",
    ),
    SelectOption(
        emoji=Ems.PepoG,
        label="Full Schedule",
        description="All pro games!"
    ),
    SelectOption(
        emoji=Ems.PepoDetective,
        label="Completed",
        description="Already finished games"
    )
]


class MySelect(ui.Select):
    def __init__(self, options, placeholder=f"Next 24h: Featured + Favourite (Default)", arg=None, author=None):
        super().__init__(placeholder=placeholder, options=options)
        self.arg = arg
        self.author = author

    async def callback(self, interaction):
        only_today = 0
        mode = 0
        favmode = 0
        match self.values[0]:
            case "Next 24h: Featured + Favourite (Default)":
                mode = 2
                only_today = 1
                favmode = 1
            case "Completed":
                mode = 3
            case "Full Schedule":
                mode = 1
            case "Featured":
                mode = 2
            case "Next 24h: Featured":
                mode = 2
                only_today = 1

        self.view.clear_items()
        view = MyView(self.author)
        view.add_item(MySelect(options, placeholder=self.values[0], arg=self.arg))
        embed = await schedule_work(self.arg, str(mode), only_today=only_today, favmode=favmode)
        await interaction.response.edit_message(embed=embed, view=view)


class MyView(ui.View):
    def __init__(self, author):
        super().__init__()
        self.author = author

    async def interaction_check(self, ntr: Interaction) -> bool:
        """
        if ntr.user and ntr.user.id in [self.author.id, Uid.irene]:
            return True
        await ntr.response.send_message(
            f'This menu cannot be controlled by you ! {Ems.peepoWTF}',
            ephemeral=True
        )
        return False
        """
        return True


class DotaSchedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Info'

    @bridge.bridge_command(
        name='schedule',
        brief=Ems.slash,
        description='Dota 2 Pro Matches Schedule',
        aliases=['sch'],
        default_permission=False,
        # guild_ids=Sid.guild_ids
    )
    @option('query', description="Enter search query, ie. `EG` (or any other team/tourney names)")
    async def schedule(self, ctx, *, query=None):
        """Get featured Dota 2 Pro Matches Schedule, use dropdown menu to view different types of schedule.\
        Use `query` to filter schedule by teams or tournaments, for example `$sch EG` will show only EG matches ;"""
        view = MyView(ctx.author)
        view.add_item(MySelect(options, arg=query, author=ctx.author))
        await ctx.respond(embed=await schedule_work(query, "2", only_today=1, favmode=1), view=view)


def setup(bot):
    bot.add_cog(DotaSchedule(bot))
