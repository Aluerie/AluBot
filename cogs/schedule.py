from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from enum import Enum

import datetime

import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands

from .utils.var import Clr, Ems
from .dota.const import DOTA_LOGO

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from .utils.bot import AluBot
    from .utils.context import Context


fav_teams = []

MATCHES_URL = 'https://liquipedia.net/dota2/Liquipedia:Upcoming_and_ongoing_matches'
LP_ICON = 'https://liquipedia.net/commons/extensions/TeamLiquidIntegration/resources/pagelogo/liquipedia_icon_menu.png'


async def schedule_work(
        session: ClientSession,
        schedule_mode: ScheduleMode,
        query: str = None,
) -> discord.Embed:
    """Main function"""

    toggle_mode = schedule_mode.toggle_mode
    only_next24 = schedule_mode.only_next24
    include_favourites = schedule_mode.include_favourites

    async with session.get(MATCHES_URL) as r:
        soup = BeautifulSoup(await r.read(), 'html.parser')
    e = discord.Embed(title='Dota 2 Pro Matches Schedule', url=MATCHES_URL, colour=Clr.prpl)
    e.set_author(name='Info from Liquipedia.net', icon_url=LP_ICON, url=MATCHES_URL)
    e.set_footer(text=schedule_mode.label_name, icon_url=DOTA_LOGO)

    dict_teams = {}
    symb_amount = 15
    dt_now = datetime.datetime.now(datetime.timezone.utc)

    def work_func(toggle: int, part=1):
        divs = soup.findAll("div", {"data-toggle-area-content": str(toggle)})
        rows = divs[-1].findAll("tbody")
        for row in rows:
            lname = row.select_one('.team-left').text.strip().replace('`', '.')
            rname = row.select_one('.team-right').text.strip().replace('`', '.')
            time_utc = row.select_one('.match-countdown').text.strip()
            dt = datetime.datetime.strptime(time_utc, '%B %d, %Y - %H:%M UTC').replace(tzinfo=datetime.timezone.utc)
            if only_next24:
                timedelta_obj = dt - dt_now
                if timedelta_obj.days > 0:
                    continue
            league = row.select_one('.match-filler').text.strip().replace(time_utc, '')

            if part == 1 and query is not None:
                do_we_post = 0
                for item in [lname, rname, league]:
                    if query in item:
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

    work_func(toggle_mode, part=1)
    if include_favourites:
        work_func(1, part=2)

    answer_str = f'Applied filter: `{query}`\n' if query is not None else ''
    answer_str += (
        f'`{"Datetime now ".ljust(symb_amount, " ")}`'
        f'{discord.utils.format_dt(dt_now, style="t")} {discord.utils.format_dt(dt_now, style="d")}\n\n'
    )

    for key, value in dict_teams.items():
        answer_str += f"**{key}**\n{chr(10).join(value)}\n"
    e.description = answer_str
    return e


select_options = [
    discord.SelectOption(
        emoji=Ems.PepoRules,
        label="Next 24h: Featured + Favourite (Default)",
        description="Featured games + some fav teams next 24 hours",
        value='1'
    ),
    discord.SelectOption(
        emoji=Ems.peepoHappyDank,
        label="Next 24h: Featured",
        description="Featured games next 24 hours",
        value='2'
    ),
    discord.SelectOption(
        emoji=Ems.bubuAyaya,
        label="Featured",
        description="Featured games by Liquidpedia",
        value='3'
    ),
    discord.SelectOption(
        emoji=Ems.PepoG,
        label="Full Schedule",
        description="All pro games!",
        value='4'
    ),
    discord.SelectOption(
        emoji=Ems.PepoDetective,
        label="Completed",
        description="Already finished games",
        value='5'
    )
]


class ScheduleMode(Enum):
    next24_featured_and_favourite = 1
    next24_featured = 2
    featured = 3
    full_shedule = 4
    completed = 5

    def __str__(self) -> str:
        return str(self.value)

    @property
    def toggle_mode(self) -> int:
        """variable that is passed to "data-toggle-area-content" div in soup parser"""
        lookup = {
            ScheduleMode.next24_featured_and_favourite: 2,
            ScheduleMode.next24_featured: 2,
            ScheduleMode.featured: 2,
            ScheduleMode.full_shedule: 1,
            ScheduleMode.completed: 3
        }
        return lookup[self]

    @property
    def only_next24(self) -> bool:
        return self.value < 3

    @property
    def include_favourites(self) -> bool:
        return self.value == 1

    @property
    def label_name(self) -> str:
        lookup = {int(i.value): i.label for i in select_options}
        return lookup[self.value]


class ScheduleSelect(discord.ui.Select):
    def __init__(self, query: str):
        super().__init__(
            options=select_options,
            placeholder='Select schedule category'
        )
        self.query = query

    async def callback(self, ntr: discord.Interaction):
        enum_sch = ScheduleMode(value=int(self.values[0]))
        e = await schedule_work(
            ntr.client.session,  # type: ignore
            enum_sch,
            self.query
        )
        await ntr.response.edit_message(embed=e)


class ScheduleView(discord.ui.View):

    def __init__(self, author: discord.User, query: str):
        super().__init__()
        self.author: discord.User = author
        self.query: str = query
        self.message: Optional[discord.Message] = None
        self.schedule_select = ss = ScheduleSelect(query)
        self.add_item(ss)

    async def interaction_check(self, ntr: discord.Interaction) -> bool:
        if ntr.user and ntr.user.id == self.author.id:
            return True
        else:
            e = await schedule_work(
                ntr.client.session,  # type: ignore
                ScheduleMode(value=int(self.schedule_select.values[0])),
                self.query
            )
            await ntr.response.send_message(embed=e, ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        if self.message:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)


class DotaSchedule(commands.Cog, name='Dota 2 Schedule'):
    """Check Pro Matches schedule

    Info is taken from Liquipedia.
    """
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.MadgeThreat)

    async def embed_worker(
            self,
            author: discord.User,
            schedule_mode: int = 1,
            query: Optional[str] = None
    ) -> (discord.Embed, discord.ui.View):
        e = await schedule_work(self.bot.session, ScheduleMode(value=schedule_mode), query)
        v = ScheduleView(author, query)
        return e, v

    @commands.command(name='schedule', aliases=['sch'])
    async def ext_schedule(self, ctx: Context, *, query: Optional[str] = None):
        """Get featured Dota 2 Pro Matches Schedule

        Use `query` to filter schedule by teams or tournaments, for example `$sch EG` will show only EG matches
        """

        e, v = await self.embed_worker(ctx.author, query=query)
        msg = await ctx.reply(embed=e, view=v)
        v.message = msg

    @app_commands.command(name='schedule')
    @app_commands.rename(schedule_mode='filter')
    @app_commands.choices(schedule_mode=[
        app_commands.Choice(name=i.label, value=int(i.value))
        for i in select_options
    ])
    async def slash_schedule(
            self,
            ntr: discord.Interaction,
            schedule_mode: Optional[int] = 1,
            query: Optional[str] = None
    ):
        """Dota 2 Pro Matches Schedule

        Parameters
        ----------
        ntr: discord.Interaction
            discord.Interaction
        schedule_mode:
            What matches to show
        query: Optional[str]
            Search filter, i.e. "EG" (or any other team/tourney names)
        """

        e, v = await self.embed_worker(ntr.user, schedule_mode=schedule_mode, query=query)
        await ntr.response.send_message(embed=e, view=v)
        v.message = await ntr.original_response()


async def setup(bot: AluBot):
    await bot.add_cog(DotaSchedule(bot))
