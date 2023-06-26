from __future__ import annotations

import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, List, MutableMapping, NamedTuple, Optional

import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands, menus

from utils import cache, const, pagination
from utils.dota.const import DOTA_LOGO
from utils.formats import format_dt_custom, format_dt_tdR

from ._category import InfoCog

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class Match(NamedTuple):
    league: str
    league_url: str
    teams: str
    twitch_url: str
    dt: datetime.datetime

    def __repr__(self) -> str:
        return f'<{self.league}, {self.teams}>'


fav_teams = []

MATCHES_URL = 'https://liquipedia.net/dota2/Liquipedia:Upcoming_and_ongoing_matches'
LIQUIPEDIA_ICON = (
    'https://liquipedia.net/commons/extensions/TeamLiquidIntegration/resources/pagelogo/liquipedia_icon_menu.png'
)
LIQUIPEDIA_BASE_URL = 'https://liquipedia.net'


def scrape_schedule_data(
    soup: BeautifulSoup,
    schedule_mode: ScheduleModeEnum,
    query: Optional[str] = None,
) -> List[Match]:
    """Get data about Dota 2 matches in a structured dictionary.

    Note: We are scraping liquipedia.net, while I think there is API, that we can/should use.

    Parameters
    ----------
    session: :class: `ClientSession`
        Session we will use to load the liquipedia page.
    schedule_mode: :class: `ScheduleModeEnum`
        Enum that defines multiple conditions for the scrap/search/filtering matches.
    query: :class: Optional[str] = None
        Text query we will limit results to.

    Returns
    -------
    List[Match]
        data about Dota 2 matches in a structured dictionary.
    """

    toggle_mode = schedule_mode.toggle_mode
    only_next24 = schedule_mode.only_next24
    include_favourites = schedule_mode.include_favourites

    matches: List[Match] = []
    dt_now = datetime.datetime.now(datetime.timezone.utc)

    def work_func(toggle: int, part=1):
        divs = soup.findAll("div", {"data-toggle-area-content": str(toggle)})
        rows = divs[-1].findAll("tbody")
        for row in rows:
            twitch_handle = row.find(class_="timer-object").get('data-stream-twitch')
            twitch_url = f'https://liquipedia.net/dota2/Special:Stream/twitch/{twitch_handle}'

            team1 = row.select_one('.team-left').text.strip().replace('`', '.')
            team2 = row.select_one('.team-right').text.strip().replace('`', '.')

            time_utc = row.select_one('.match-countdown').text.strip()
            dt = datetime.datetime.strptime(time_utc, '%B %d, %Y - %H:%M UTC').replace(tzinfo=datetime.timezone.utc)

            if only_next24:
                timedelta_obj = dt - dt_now
                if timedelta_obj.days > 0:
                    continue

            league: str = row.select_one('.match-filler').text.strip().replace(time_utc, '')
            league_url = row.find(class_="league-icon-small-image").find('a').get('href')

            if part == 1 and query is not None:
                do_we_post = 0
                for item in [team1, team2, league]:
                    if query in item:
                        do_we_post = 1
                if not do_we_post:
                    continue

            if part == 2:
                do_we_post = 0
                for item in [team1, team2]:
                    if item in fav_teams:
                        do_we_post = 1
                if not do_we_post:
                    continue

            matches.append(
                Match(
                    league=league.lstrip(),
                    league_url=league_url,
                    teams=f'{team1} - {team2}',
                    twitch_url=twitch_url,
                    dt=dt,
                )
            )

    work_func(toggle_mode, part=1)
    if include_favourites:
        work_func(1, part=2)

    return matches


select_options = [
    discord.SelectOption(
        emoji=const.Emote.PepoRules,
        label="Next 24h: Featured + Favourite (Default)",
        description="Featured games + some fav teams next 24 hours",
        value='1',
    ),
    discord.SelectOption(
        emoji=const.Emote.peepoHappyDank,
        label="Next 24h: Featured",
        description="Featured games next 24 hours",
        value='2',
    ),
    discord.SelectOption(
        emoji=const.Emote.bubuAyaya, label="Featured", description="Featured games by Liquidpedia", value='3'
    ),
    discord.SelectOption(emoji=const.Emote.PepoG, label="Full Schedule", description="All pro games!", value='4'),
    discord.SelectOption(
        emoji=const.Emote.PepoDetective, label="Completed", description="Already finished games", value='5'
    ),
]


class ScheduleModeEnum(Enum):
    next24_featured_and_favourite = 1
    next24_featured = 2
    featured = 3
    full_schedule = 4
    completed = 5

    def __str__(self) -> str:
        return str(self.value)

    @property
    def toggle_mode(self) -> int:
        """variable that is passed to "data-toggle-area-content" div in soup parser"""
        lookup = {
            ScheduleModeEnum.next24_featured_and_favourite: 2,
            ScheduleModeEnum.next24_featured: 2,
            ScheduleModeEnum.featured: 2,
            ScheduleModeEnum.full_schedule: 1,
            ScheduleModeEnum.completed: 3,
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
    def __init__(self, author: discord.User | discord.Member, soup: BeautifulSoup, query: Optional[str] = None):
        super().__init__(options=select_options, placeholder='\N{SPIRAL CALENDAR PAD}Select schedule category')
        self.query: Optional[str] = query
        self.soup: BeautifulSoup = soup
        self.author: discord.User | discord.Member = author

    async def callback(self, ntr: discord.Interaction[AluBot]):
        sch_enum = ScheduleModeEnum(value=int(self.values[0]))
        pages = SchedulePages(ntr, self.soup, sch_enum, self.query)
        await pages.start(edit_response=True)

    async def interaction_check(self, ntr: discord.Interaction[AluBot]) -> bool:
        if ntr.user and ntr.user.id == self.author.id:
            return True
        else:
            sch_enum = ScheduleModeEnum(value=int(self.values[0]))
            pages = SchedulePages(ntr, self.soup, sch_enum, self.query)
            await pages.start(ephemeral=True)
            return False


class SchedulePageSource(menus.ListPageSource):
    def __init__(
        self,
        author: discord.User | discord.Member,
        soup: BeautifulSoup,
        schedule_enum: ScheduleModeEnum,
        query: Optional[str] = None,
    ):
        initial_data = scrape_schedule_data(soup, schedule_enum, query)
        initial_data.sort(key=lambda x: (x.league, x.dt))
        super().__init__(entries=initial_data, per_page=20)
        self.schedule_enum = schedule_enum
        self.author: discord.User | discord.Member = author
        self.query: Optional[str] = query

    async def format_page(self, menu: SchedulePages, matches: List[Match]):
        e = discord.Embed(title='Dota 2 Pro Matches Schedule', url=MATCHES_URL, colour=0x042B4C)
        e.set_author(name='Info from Liquipedia.net', icon_url=LIQUIPEDIA_ICON, url=MATCHES_URL)
        e.set_footer(text=self.schedule_enum.label_name, icon_url=DOTA_LOGO)

        dt_now = datetime.datetime.now(datetime.timezone.utc)

        # find the longest team versus string like "Secret - PSG.LGD"
        
        desc = f'Applied filter: `{self.query}`\n' if self.query is not None else ''
        if not matches:
            desc += 'No matches were found for the category/query.'
            e.description = desc
            return e

        match_with_longest_teams = max(matches, key=lambda x: len(x.teams))
        max_amount_of_chars = len(match_with_longest_teams.teams)
        desc += f'`{"Datetime now ".ljust(max_amount_of_chars, " ")}`{format_dt_custom(dt_now, "t", "d")}\n'

        # matches.sort(key=lambda x: (x.league, x.dt))
        # now it's sorted by leagues and dt

        league: str | None = None
        previous_match_dt: datetime.datetime | None = None

        for match in matches:
            if league != match.league:
                desc += f"\n[**{match.league}**]({LIQUIPEDIA_BASE_URL}{match.league_url})\n"
                league = match.league
                previous_match_dt = None

            if previous_match_dt and match.dt - previous_match_dt > datetime.timedelta(hours=6):
                desc += '\n'
            previous_match_dt = match.dt

            desc += (
                f"[`{match.teams.ljust(max_amount_of_chars, ' ')}`]({match.twitch_url})"
                f"{format_dt_custom(match.dt, 't', 'R')}\n"
            )

        e.description = desc
        return e


class SchedulePages(pagination.Paginator):
    source: SchedulePageSource

    def __init__(
        self,
        ctx: AluContext | discord.Interaction[AluBot],
        soup: BeautifulSoup,
        schedule_enum: ScheduleModeEnum,
        query: Optional[str] = None,
    ):
        source = SchedulePageSource(ctx.user, soup, schedule_enum, query)
        super().__init__(ctx, source)
        self.add_item(ScheduleSelect(ctx.user, soup, query))


class Schedule(InfoCog, name='Schedules', emote=const.Emote.DankMadgeThreat):
    """Check Pro Matches schedule.

    Currently, the bot supports Dota 2 and football.
    """

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.soup_cache: MutableMapping[str, BeautifulSoup] = cache.ExpiringCache(seconds=1800.0)

    async def get_soup(self, key: str) -> BeautifulSoup:
        if soup := self.soup_cache.get(key):
            return soup
        else:
            async with self.bot.session.get(MATCHES_URL) as r:
                soup = BeautifulSoup(await r.read(), 'html.parser')
                self.soup_cache[key] = soup
                return soup

    @commands.hybrid_command(aliases=['sch'])
    @app_commands.rename(schedule_mode='filter')
    @app_commands.choices(schedule_mode=[app_commands.Choice(name=i.label, value=int(i.value)) for i in select_options])
    async def schedule(self, ctx: AluContext, schedule_mode: int = 1, query: Optional[str] = None):
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
        await ctx.typing()
        soup = await self.get_soup('dota2')
        schedule_enum = ScheduleModeEnum(value=schedule_mode)
        pages = SchedulePages(ctx, soup, schedule_enum, query)
        await pages.start()

    @commands.hybrid_command()
    async def fixtures(self, ctx: AluContext):
        """Get football fixtures"""
        url = "https://onefootball.com/en/competition/premier-league-9/fixtures"
        async with self.bot.session.get(url) as r:
            soup = BeautifulSoup(await r.read(), 'html.parser')
            fixtures = soup.find('of-match-cards-list')
            if fixtures:
                # game_week = fixtures.find('h3', attrs={'class': 'section-header__subtitle'})
                # print(game_week.text)
                # i dont actually know if the following type: ignore is safe
                matches = fixtures.findAll('li', attrs={'class': 'simple-match-cards-list__match-card'})  # type: ignore
                match_strings = []
                for match in matches:
                    team_content = match.findAll(
                        'of-simple-match-card-team', attrs={'class': 'simple-match-card__team-content'}
                    )
                    team1 = team_content[0].find('span', attrs={'class': 'simple-match-card-team__name'}).text
                    team2 = team_content[1].find('span', attrs={'class': 'simple-match-card-team__name'}).text
                    pre_match_data = match.find('span', attrs={'class': 'simple-match-card__pre-match'})
                    if pre_match_data is not None:
                        match_time = match.find('span', attrs={'class': 'simple-match-card__pre-match'}).find('time')[
                            'datetime'
                        ]
                        dt = datetime.datetime.strptime(match_time, '%Y-%m-%dT%H:%M:%SZ').replace(
                            tzinfo=datetime.timezone.utc
                        )
                        teams = f'{team1} - {team2}'.ljust(40, " ")
                        match_strings.append(f'`{teams}` {format_dt_tdR(dt)}')

                e = discord.Embed(colour=0xE0FA51, title='Premier League Fixtures', url=url)
                e.description = '\n'.join(match_strings)
                e.set_author(name='Info from onefootball.com', url=url, icon_url='https://i.imgur.com/pm2JgEW.jpg')
                await ctx.reply(embed=e)
            else:
                e = discord.Embed(colour=const.Colour.error())
                e.description = 'No matches found'
                await ctx.reply(embed=e, ephemeral=True)


async def setup(bot: AluBot):
    await bot.add_cog(Schedule(bot))
