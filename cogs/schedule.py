from __future__ import annotations
from typing import TYPE_CHECKING, Optional

import datetime

import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands

from .utils.var import Clr, Img, Ems

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from .utils.bot import AluBot
    from .utils.context import Context


fav_teams = []


async def schedule_work(
        session: ClientSession,
        arg,
        mod,
        only_today: bool = False,
        favourite_mode: bool = False
) -> discord.Embed:
    url = 'https://liquipedia.net/dota2/Liquipedia:Upcoming_and_ongoing_matches'
    async with session.get(url) as r:
        soup = BeautifulSoup(await r.read(), 'html.parser')
    e = discord.Embed(title='Dota 2 Pro Matches Schedule', url=url, colour=Clr.prpl)
    e.set_author(name='Info from Liquipedia.net', icon_url=Img.dota2logo, url=url)

    dict_teams = {}
    symb_amount = 15
    dt_now = datetime.datetime.now(datetime.timezone.utc)

    def work_func(modmod, part=1):
        divs = soup.findAll("div", {"data-toggle-area-content": modmod})
        rows = divs[-1].findAll("tbody")
        for row in rows:
            lname = row.select_one('.team-left').text.strip().replace('`', '.')
            rname = row.select_one('.team-right').text.strip().replace('`', '.')
            time_utc = row.select_one('.match-countdown').text.strip()
            dt = datetime.datetime.strptime(time_utc, '%B %d, %Y - %H:%M UTC').replace(tzinfo=datetime.timezone.utc)
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
            answer = (
                f"`{teams.ljust(symb_amount, ' ')}`"
                f"{discord.utils.format_dt(dt, style='t')} {discord.utils.format_dt(dt, style='R')}"
            )
            if answer not in dict_teams[league]:  # remove duplicates if any
                dict_teams[league].append(answer)

    work_func(mod, part=1)
    if favourite_mode == 1:
        work_func("1", part=2)

    answer_str = f'Applied filter: `{arg}`\n' if arg is not None else ''
    answer_str += (
        f'`{"Datetime now ".ljust(symb_amount, " ")}`'
        f'{discord.utils.format_dt(dt_now, style="t")} {discord.utils.format_dt(dt_now, style="d")}\n\n'
    )

    for key, value in dict_teams.items():
        answer_str += f"**{key}**\n{chr(10).join(value)}\n"
    e.description = answer_str
    return e


options = [
    discord.SelectOption(
        label="Next 24h: Featured + Favourite (Default)", emoji=Ems.PepoRules,
        description="Featured games + some fav teams next 24 hours"
    ),
    discord.SelectOption(
        label="Next 24h: Featured", emoji=Ems.peepoHappyDank,
        description="Featured games next 24 hours"
    ),
    discord.SelectOption(
        label="Featured", emoji=Ems.bubuAyaya,
        description="Featured games by Liquidpedia"
    ),
    discord.SelectOption(
        label="Full Schedule", emoji=Ems.PepoG,
        description="All pro games!"
    ),
    discord.SelectOption(
        label="Completed", emoji=Ems.PepoDetective,
        description="Already finished games"
    )
]


class MySelect(discord.ui.Select):
    def __init__(self, options, placeholder=f"Next 24h: Featured + Favourite (Default)", arg=None, author=None):
        super().__init__(placeholder=placeholder, options=options)
        self.arg = arg
        self.author: discord.User = author

    async def callback(self, ntr: discord.Interaction):
        mode, only_today, fav_mode = 0, False, False
        match self.values[0]:
            case "Next 24h: Featured + Favourite (Default)":
                mode, only_today, fav_mode = 2, True, True
            case "Completed":
                mode = 3
            case "Full Schedule":
                mode = 1
            case "Featured":
                mode = 2
            case "Next 24h: Featured":
                mode, only_today = 2, True

        self.view.clear_items()
        view = MyView(self.author)
        view.add_item(MySelect(options, placeholder=self.values[0], arg=self.arg))
        e = await schedule_work(
            ntr.client.session,  # type: ignore
            self.arg, str(mode), only_today=only_today, favourite_mode=fav_mode
        )
        await ntr.response.edit_message(embed=e, view=view)


class MyView(discord.ui.View):
    def __init__(self, author: discord.User):
        super().__init__()
        self.author: discord.User = author

    async def interaction_check(self, ntr: discord.Interaction) -> bool:
        """
        if ntr.user and ntr.user.id != self.author.id:
            return True
        await ntr.response.send_message(
            f'This menu cannot be controlled by you ! {Ems.peepoWTF}',
            ephemeral=True
        )
        return False
        """
        return True


class DotaSchedule(commands.Cog, name='Dota 2 Schedule'):
    """Check Pro Matches schedule

    Info is taken from Liquipedia.
    """
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.MadgeThreat)

    @commands.hybrid_command(
        name='schedule',
        description='Dota 2 Pro Matches Schedule',
        aliases=['sch'],
        default_permission=False,
        # guild_ids=Sid.guild_ids
    )
    @app_commands.describe(query="Enter search query, ie. `EG` (or any other team/tourney names)")
    async def schedule(self, ctx: Context, *, query: Optional[str]):
        """Get featured Dota 2 Pro Matches Schedule, use dropdown menu to view different types of schedule.\
        Use `query` to filter schedule by teams or tournaments, for example `$sch EG` will show only EG matches ;"""
        view = MyView(ctx.author)
        view.add_item(MySelect(options, arg=query, author=ctx.author))
        await ctx.reply(
            embed=await schedule_work(self.bot.session, query, "2", only_today=True, favourite_mode=True),
            view=view
        )


async def setup(bot: AluBot):
    await bot.add_cog(DotaSchedule(bot))
