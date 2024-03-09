from __future__ import annotations

import datetime
import logging
from enum import Enum
from typing import TYPE_CHECKING, Any, NamedTuple, override

import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands, menus

from utils import cache, const, formats, pages

from ._base import InfoCog

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from bot import AluBot
    from utils import AluContext

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Match(NamedTuple):
    league: str
    league_url: str
    teams: str
    twitch_url: str
    dt: datetime.datetime

    @override
    def __repr__(self) -> str:
        return f"<{self.league}, {self.teams}>"


MATCHES_URL = "https://liquipedia.net/dota2/Liquipedia:Upcoming_and_ongoing_matches"
LIQUIPEDIA_ICON = (
    "https://liquipedia.net/commons/extensions/TeamLiquidIntegration/resources/pagelogo/liquipedia_icon_menu.png"
)
LIQUIPEDIA_BASE_URL = "https://liquipedia.net"


def scrape_schedule_data(
    soup: BeautifulSoup,
    schedule_mode: ScheduleModeEnum,
    query: str | None = None,
) -> list[Match]:
    """Get data about Dota 2 matches in a structured dictionary.

    Note: We are scraping liquipedia.net, while I think there is API, that we can/should use.

    Parameters
    ----------
    session : ClientSession
        Session we will use to load the liquipedia page.
    schedule_mode : ScheduleModeEnum
        Enum that defines multiple conditions for the scrap/search/filtering matches.
    query : str | None = None
        Text query we will limit results to.

    Returns
    -------
    list[Match]
        data about Dota 2 matches in a structured dictionary.

    """
    matches: list[Match] = []

    dt_now = datetime.datetime.now(datetime.UTC)
    divs = soup.findAll("div", {"data-toggle-area-content": schedule_mode.data_toggle_area_content})
    match_rows = divs[-1].findAll("tbody")

    def get_dt_and_twitch_url(match_row: Any) -> tuple[datetime.datetime, str]:
        timer = match_row.find(class_="timer-object")
        timestamp = timer.get("data-timestamp")
        # timestamp is given in local machine time
        dt = datetime.datetime.fromtimestamp(int(timestamp)).astimezone(datetime.UTC)
        twitch_url = f"https://liquipedia.net/dota2/Special:Stream/twitch/{timer.get('data-stream-twitch')}"
        return dt, twitch_url

    for match_row in match_rows:
        dt, twitch_url = get_dt_and_twitch_url(match_row)

        if schedule_mode.only_next_game_day and (dt - dt_now).days > 0:
            # we do not want this and next matches, since it's too far in future (we only want next 24 hours.)
            break

        team1 = match_row.select_one(".team-left").text.strip().replace("`", ".")
        team2 = match_row.select_one(".team-right").text.strip().replace("`", ".")
        # print(dt, (dt - dt_now).days, team1, team2)
        league = match_row.find(class_="league-icon-small-image").find("a")
        league_title = league.get("title")
        league_url = league.get("href")

        if query is not None and not any(query in item for item in [team1, team2, league_title]):
            continue

        matches.append(
            Match(
                league=league_title,
                league_url=league_url,
                teams=f"{team1} - {team2}",
                twitch_url=twitch_url,
                dt=dt,
            )
        )

    return matches


SELECT_OPTIONS = [
    discord.SelectOption(
        emoji=const.Emote.PepoRules,
        label="Next GameDay: Featured",
        description="Featured games for the closest GameDay",
        value="1",
    ),
    discord.SelectOption(
        emoji=const.Emote.peepoHappyDank,
        label="Featured",
        description="Featured games by Liquidpedia",
        value="2",
    ),
    discord.SelectOption(
        emoji=const.Emote.PepoG,
        label="Full Schedule",
        description="All pro games!",
        value="3",
    ),
    discord.SelectOption(
        emoji=const.Emote.PepoDetective,
        label="Completed",
        description="Already finished games",
        value="4",
    ),
]


class ScheduleModeEnum(Enum):
    next_game_day_featured = 1
    featured = 2
    full_schedule = 3
    completed = 4

    @override
    def __str__(self) -> str:
        return str(self.value)

    @property
    def data_toggle_area_content(self) -> str:
        """Variable that is passed to "data-toggle-area-content" div in soup parser."""
        lookup = {
            ScheduleModeEnum.next_game_day_featured: "2",
            ScheduleModeEnum.featured: "2",
            ScheduleModeEnum.full_schedule: "1",
            ScheduleModeEnum.completed: "3",
        }
        return lookup[self]

    @property
    def only_next_game_day(self) -> bool:
        return self.value == 1

    @property
    def label_name(self) -> str:
        lookup = {int(i.value): i.label for i in SELECT_OPTIONS}
        return lookup[self.value]


class SchedulePageSource(menus.ListPageSource):
    def __init__(
        self,
        author: discord.User | discord.Member,
        soup: BeautifulSoup,
        schedule_enum: ScheduleModeEnum,
        query: str | None = None,
    ) -> None:
        initial_data = scrape_schedule_data(soup, schedule_enum, query)
        initial_data.sort(key=lambda x: (x.league, x.dt))
        super().__init__(entries=initial_data, per_page=20)
        self.schedule_enum = schedule_enum
        self.author: discord.User | discord.Member = author
        self.query: str | None = query

    @override
    async def format_page(self, menu: SchedulePages, matches: list[Match]) -> discord.Embed:
        embed = (
            discord.Embed(
                colour=0x042B4C,
                title="Dota 2 Pro Matches Schedule",
                url=MATCHES_URL,
            )
            .set_author(name="Info from Liquipedia.net", icon_url=LIQUIPEDIA_ICON, url=MATCHES_URL)
            .set_footer(text=self.schedule_enum.label_name, icon_url=const.Logo.Dota)
        )

        dt_now = datetime.datetime.now(datetime.UTC)

        # find the longest team versus string like "Secret - PSG.LGD"

        desc = f"Applied filter: `{self.query}`\n" if self.query is not None else ""
        if not matches:
            desc += "No matches were found for the category/query."
            embed.description = desc
            return embed

        match_with_longest_teams = max(matches, key=lambda x: len(x.teams))
        max_amount_of_chars = len(match_with_longest_teams.teams)
        desc += f'`{"Datetime now ".ljust(max_amount_of_chars, " ")}`{formats.format_dt_custom(dt_now, "t", "d")}\n'

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
                desc += "\n"
            previous_match_dt = match.dt

            desc += (
                f"[`{match.teams.ljust(max_amount_of_chars, ' ')}`]({match.twitch_url})"
                f"{formats.format_dt_custom(match.dt, 't', 'R')}\n"
            )

        embed.description = desc
        return embed


class SchedulePages(pages.Paginator):
    source: SchedulePageSource

    def __init__(
        self,
        ctx: AluContext | discord.Interaction[AluBot],
        soup: BeautifulSoup,
        schedule_enum: ScheduleModeEnum,
        query: str | None = None,
    ) -> None:
        source = SchedulePageSource(ctx.user, soup, schedule_enum, query)
        super().__init__(ctx, source)
        self.add_item(ScheduleSelect(ctx.user, soup, query))


class ScheduleSelect(discord.ui.Select[SchedulePages]):
    def __init__(self, author: discord.User | discord.Member, soup: BeautifulSoup, query: str | None = None) -> None:
        super().__init__(options=SELECT_OPTIONS, placeholder="\N{SPIRAL CALENDAR PAD} Select schedule category")
        self.query: str | None = query
        self.soup: BeautifulSoup = soup
        self.author: discord.User | discord.Member = author

    @override
    async def callback(self, interaction: discord.Interaction[AluBot]) -> None:
        sch_enum = ScheduleModeEnum(value=int(self.values[0]))
        p = SchedulePages(interaction, self.soup, sch_enum, self.query)
        await p.start(edit_response=True)

    @override
    async def interaction_check(self, interaction: discord.Interaction[AluBot]) -> bool:
        if interaction.user and interaction.user.id == self.author.id:
            return True
        else:
            schedule_enum = ScheduleModeEnum(value=int(self.values[0]))
            p = SchedulePages(interaction, self.soup, schedule_enum, self.query)
            await p.start(ephemeral=True)
            return False


class Schedule(InfoCog, name="Schedules", emote=const.Emote.DankMadgeThreat):
    """Check Pro Matches schedule.

    Currently, the bot supports Dota 2 and football.
    """

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.soup_cache: MutableMapping[str, BeautifulSoup] = cache.ExpiringCache(seconds=1800.0)  # 30 minutes

    async def get_soup(self, key: str) -> BeautifulSoup:
        if soup := self.soup_cache.get(key):
            return soup
        else:
            async with self.bot.session.get(MATCHES_URL) as r:
                soup = BeautifulSoup(await r.read(), "html.parser")
                self.soup_cache[key] = soup
                return soup

    @commands.hybrid_command(aliases=["sch"])
    @app_commands.rename(schedule_mode="filter")
    @app_commands.choices(schedule_mode=[app_commands.Choice(name=i.label, value=int(i.value)) for i in SELECT_OPTIONS])
    async def schedule(self, ctx: AluContext, schedule_mode: int = 1, query: str | None = None) -> None:
        """Dota 2 Pro Matches Schedule.

        Parameters
        ----------
        schedule_mode : int
            What matches to show
        query : str | None
            Search filter, i.e. "EG", "ESL" (or any other team/tournament names)

        """
        await ctx.typing()
        soup = await self.get_soup("dota2")
        schedule_enum = ScheduleModeEnum(value=schedule_mode)
        p = SchedulePages(ctx, soup, schedule_enum, query)
        await p.start()

    @commands.hybrid_command()
    async def fixtures(self, ctx: AluContext) -> None:
        """Get football fixtures."""
        url = "https://onefootball.com/en/competition/premier-league-9/fixtures"
        async with self.bot.session.get(url) as r:
            soup = BeautifulSoup(await r.read(), "html.parser")
            fixtures = soup.find("of-match-cards-list")
            if fixtures:
                # game_week = fixtures.find('h3', attrs={'class': 'section-header__subtitle'})
                # print(game_week.text)
                # i dont actually know if the following type: ignore is safe
                matches = fixtures.findAll("li", attrs={"class": "simple-match-cards-list__match-card"})  # type: ignore
                match_strings = []
                for match in matches:
                    team_content = match.findAll(
                        "of-simple-match-card-team", attrs={"class": "simple-match-card__team-content"}
                    )
                    team1 = team_content[0].find("span", attrs={"class": "simple-match-card-team__name"}).text
                    team2 = team_content[1].find("span", attrs={"class": "simple-match-card-team__name"}).text
                    pre_match_data = match.find("span", attrs={"class": "simple-match-card__pre-match"})
                    if pre_match_data is not None:
                        match_time = match.find("span", attrs={"class": "simple-match-card__pre-match"}).find("time")[
                            "datetime"
                        ]
                        dt = datetime.datetime.strptime(match_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC)
                        teams = f"{team1} - {team2}".ljust(40, " ")
                        match_strings.append(f"`{teams}` {formats.format_dt_tdR(dt)}")

                e = discord.Embed(colour=0xE0FA51, title="Premier League Fixtures", url=url)
                e.description = "\n".join(match_strings)
                e.set_author(name="Info from onefootball.com", url=url, icon_url="https://i.imgur.com/pm2JgEW.jpg")
                await ctx.reply(embed=e)
            else:
                e = discord.Embed(colour=const.Colour.maroon)
                e.description = "No matches found"
                await ctx.reply(embed=e, ephemeral=True)


async def setup(bot: AluBot) -> None:
    await bot.add_cog(Schedule(bot))
