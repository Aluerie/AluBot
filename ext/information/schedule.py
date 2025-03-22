from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import discord
from bs4 import BeautifulSoup
from discord import app_commands

from bot import AluCog
from utils import const, fmt

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Schedule(AluCog, name="Schedules", emote=const.Emote.DankMadgeThreat):
    """Check Pro Matches schedule.

    Currently, the bot supports Dota 2 and football.
    """

    @app_commands.command()
    async def fixtures(self, interaction: AluInteraction) -> None:
        """Get football fixtures."""
        url = "https://onefootball.com/en/competition/premier-league-9/fixtures"
        async with self.bot.session.get(url) as r:
            soup = BeautifulSoup(await r.read(), "html.parser")
            fixtures = soup.find("of-match-cards-list")
            if fixtures:
                # game_week = fixtures.find('h3', attrs={'class': 'section-header__subtitle'})
                # print(game_week.text)
                matches = fixtures.findAll("li", attrs={"class": "simple-match-cards-list__match-card"})  # type:ignore[reportAttributeAccessIssue]
                match_strings = []
                for match in matches:
                    team_content = match.findAll(
                        "of-simple-match-card-team",
                        attrs={"class": "simple-match-card__team-content"},
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
                        match_strings.append(f"`{teams}` {fmt.format_dt_tdR(dt)}")

                embed = discord.Embed(
                    color=0xE0FA51,
                    title="Premier League Fixtures",
                    url=url,
                    description="\n".join(match_strings),
                ).set_author(
                    name="Info from onefootball.com",
                    url=url,
                    icon_url="https://i.imgur.com/pm2JgEW.jpg",
                )
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    color=const.Color.error,
                    description="No matches found",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Schedule(bot))
