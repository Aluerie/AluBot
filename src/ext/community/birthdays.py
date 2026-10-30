"""Birthdays.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import calendar
import datetime
import enum
import operator
import random
import zoneinfo
from typing import TYPE_CHECKING, Final, NotRequired, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands

from core import Cog, TransformTimeZone
from shared import clock, errors
from utils import const, pages, prompts

if TYPE_CHECKING:
    from core import Bot, Interaction, Timer

    class BirthdayTimerData(TypedDict):
        user_id: int
        year: int  # 1900 if the user didn't tell the year
        month: NotRequired[int]  # timers created by earlier versions don't have `month` and `day`
        day: NotRequired[int]

    class RemoveRoleTimerData(TypedDict):
        user_id: int


__all__ = ("Birthdays",)

UNKNOWN_YEAR = 1900
"""Year that is stored when the user doesn't want to tell the year of their birth."""
MIN_YEAR = UNKNOWN_YEAR + 1
"""The earliest year of birth that can be entered."""
STALE_AFTER = datetime.timedelta(days=1)
"""If the bot was down for longer than this since the birthday, congratulating "today" is pointless."""


CONGRATULATION_TEXT_BANK = (
    "I hope your special day will bring you lots of happiness, love, and fun. You deserve them a lot. Enjoy!",
    "All things are sweet and bright. May you have a lovely birthday Night.",
    "Don't ever change! Stay as amazing as you are, my friend",
    "Let's light the candles and celebrate this special day of your life. Happy birthday.",
    "Here's to the sweetest and loveliest person I know. Happy birthday!",
    "Happy birthday to my best friend, the one I care about the most!",
    "Wherever your feet may take, whatever endeavor you lay hands on. It will always be successful. Happy birthday.",
    "May this special day bring you endless joy and tons of precious memories!",
    "You are very special and that's why you need to float with lots of smiles on your lovely face. Happy birthday.",
    "It's as simple as ABC; today makes more sense because of you, Happy birthday.",
    "Let your all the dreams to be on fire and light your birthday candles with that. Have a gorgeous birthday.",
    "May you continue to improve as a person with each passing year. Wishing you a very happy birthday.",
    (
        "Today is the birthday of the person who is spreading joy and positivity all around. May your birthday "
        "and your life be as wonderful as you are!"
    ),
    "Happy birthday! Here's to a bright, healthy and exciting future!",
    "The joy is in the air because your special day is here!",
    "Your birthday only comes once a year, so make sure this is the most memorable one ever and have a colorful day.",
    "Today I wish you a fun time, shared with your dear ones, and a lifelong happiness!",
    "Wishing you a wonderful day and all the most amazing things on your Big Day!",
    "Life is tough but birthdays are smooth because I will finally have a chance to smile at you. Happy birthday.",
    "May your birthday be full of happy hours and special moments to remember for a long long time!",
    (
        "Soon you're going to start a new year of your life and "
        "I hope this coming year will bring every success you deserve. Happy birthday."
    ),
    "Wishing you a memorable day and an adventurous year, Happy birthday",
    "Hope your birthday is as wonderful and extraordinary as you are.",
    "I wish you to enjoy your special day, relax and let yourself be spoiled, you deserve it!",
    "I wish you to have a wonderful time on your Day!",
    "I wish that life brings you a beautiful surprise for every candle on your bday cake!",
    "Hugging you don't need any reason but, if there is a reason, more than one hug is a norm. Happy Birthday!",
    "I wish you a day filled with great fun and a year filled with true happiness!",
    "Let yourself do everything that you like most in life, may your Big Day be cheerful and happy!",
    "Wishing you the abundance of fun and glory, Happy Birthday!",
    "May this day be so happy that smile never fades away from your face.",
    "On your birthday friends wish you many things, but I will wish you only two: always and never. "
    "Never feel blue and always be happy!",
    "May the dream that means most to you, start coming true this year. Happy Bday!",
    "May you enjoy your special day to the fullest extent, buddy!",
    "With you, it is always about bringing in fun, in more ways than one, come rain come sun, just fun. Happy Birthday!",
    "May your birthday mark the beginning of a wonderful period of time in your life!",
    "My dear friend, may your special day be full of beautiful, magical and unforgettable moments!",
    "Happy birthday, gorgeous! You are another year older and I just can't see it. Have a blast! "
    "Wishing you the best of the best!",
    "Wishing you greatest birthday ever, full of love and joy from the moment you open your eyes in the morning "
    "until you sleep for the night.",
)

GIF_URLS_BANK = (
    "https://media.tenor.com/1xto23A6M6UAAAAC/happy-birthday-office.gif",
    "https://media.tenor.com/CgwgbFV8tzUAAAAC/the-office-birthday-fun.gif",
    "https://media.tenor.com/ufuYtIqIsIgAAAAC/friends-birthday.gif",
    "https://media.tenor.com/J6VTVKf270UAAAAC/leonardo-dicaprio-cheers.gif",
    "https://media.tenor.com/7xCchAIgDXMAAAAC/barbie-margot-robbie.gif",
    "https://media.tenor.com/ZRTc4ocgdN4AAAAC/birthday-travolta.gif",
    "https://media.tenor.com/4UhjvIJLNSoAAAAC/bday-friends.gif",
    "https://media.tenor.com/zrpw1WuYPBUAAAAC/its-the-biggest-night-of-the-year-eric-cartman.gif",
    "https://media.tenor.com/KnWD3xyzkV4AAAAd/happy-birthday-gifts.gif",
)


class Month(enum.IntEnum):
    """Months for the slash command choices (the names are what users see)."""

    January = 1
    February = 2
    March = 3
    April = 4
    May = 5
    June = 6
    July = 7
    August = 8
    September = 9
    October = 10
    November = 11
    December = 12


def birthday_fmt(month: int, day: int, year: int) -> str:
    """Format a date to show in the bot's embeds.

    Parameters
    ----------
    month
        Month of the birthday.
    day
        Day of the birthday.
    year
        Year of the birth. `UNKNOWN_YEAR` hides it.

    Returns
    -------
    str
        Date like "28/August/2025" (or "28/August" if the year is unknown).
    """
    text = f"{day:02d}/{Month(month).name}"
    return text if year == UNKNOWN_YEAR else f"{text}/{year}"


def birthday_in_year(month: int, day: int, year: int) -> datetime.date:
    """Get the date of a birthday in the given year.

    People born on the 29th of February celebrate on the 28th of February in non-leap years.
    """
    if month == 2 and day == 29 and not calendar.isleap(year):  # noqa: PLR2004
        day = 28
    return datetime.date(year, month, day)


def next_birthday_date(month: int, day: int, *, on_or_after: datetime.date) -> datetime.date:
    """Get the first date of the birthday that is not earlier than `on_or_after`."""
    date = birthday_in_year(month, day, on_or_after.year)
    if date < on_or_after:
        date = birthday_in_year(month, day, on_or_after.year + 1)
    return date


def start_of_day(date: datetime.date, tzinfo: datetime.tzinfo) -> datetime.datetime:
    """Get the very beginning of the date in the given timezone (aware)."""
    return datetime.datetime.combine(date, datetime.time(), tzinfo=tzinfo)


def month_and_day(timer: Timer[BirthdayTimerData]) -> tuple[int, int]:
    """Get the month and the day of the birthday of the timer.

    Timers created by the earlier versions of the bot don't store them,
    but they can be restored from the moment of the timer in the timer's timezone.
    """
    data = timer.data
    if "month" in data and "day" in data:
        return data["month"], data["day"]
    local = timer.expires_at.astimezone(zoneinfo.ZoneInfo(timer.timezone))
    return local.month, local.day


class Birthdays(Cog):
    """Set your birthday and get congratulations from the bot.

    There is a special role in Eileen's server
    which on your birthday gives you a priority in the members list and makes the bot
    congratulate you.
    """

    # TODO: fill these in. They were part of the old `bot.community` helper object which does not exist anymore.
    BIRTHDAY_CHANNEL_ID: Final = const.ChannelId(748604236190842881)
    """Channel where the birthday congratulations are sent."""
    BIRTHDAY_ROLE_ID: Final = const.RoleId(748586533627363469)
    """Role that is given to people for the day of their birthday."""
    BLACKLISTED_ROLE_ID: Final = const.RoleId(0)
    """Members with this role are not congratulated. Leave `0` if there is no such role."""

    TEST_CHANNEL_ID: Final = const.ChannelId(724986090632642653)
    """Channel where the test bot sends congratulations instead (it's the bot spam channel)."""

    @override
    async def cog_load(self) -> None:
        if not (self.BIRTHDAY_CHANNEL_ID and self.BIRTHDAY_ROLE_ID):
            msg = "Birthdays: BIRTHDAY_CHANNEL_ID and BIRTHDAY_ROLE_ID have to be filled in."
            raise RuntimeError(msg)
        await super().cog_load()

    @property
    def birthday_channel(self) -> discord.TextChannel:
        """The channel where birthday notifications are sent."""
        return self.bot.get_text_channel_or_test(self.BIRTHDAY_CHANNEL_ID)

    @property
    def birthday_role(self) -> discord.Role:
        """The role that is given to people on their birthday."""
        role = self.bot.community.get_role(self.BIRTHDAY_ROLE_ID)
        if role is None:
            msg = f"Birthday role {self.BIRTHDAY_ROLE_ID} is not found in the community guild."
            raise LookupError(msg)
        return role

    birthday_group = app_commands.Group(
        name="birthday",
        description="Birthday related commands.",
        guild_ids=[const.Guild.community],
    )

    ####################################################################################################################
    # COMMANDS
    ####################################################################################################################

    @birthday_group.command(name="set")
    async def birthday_set(
        self,
        interaction: Interaction,
        day: app_commands.Range[int, 1, 31],
        month: Month,
        timezone: TransformTimeZone,
        year: int | None = None,
    ) -> None:
        """Set your birthday.

        Parameters
        ----------
        day
            Day of your birthday, number from 1 till 31.
        month
            Month of your birthday, full month name.
        timezone
            Timezone, type and pick from the autocomplete or try IANA alias or country/city names.
        year
            Year of your birth, optional.
        """
        now = clock.utcnow()
        tzinfo = timezone.to_tzinfo()

        try:
            # the year only matters for the validity of the date, so for an unknown year pick a leap one (29 Feb)
            datetime.date(year or 2000, month, day)
        except ValueError:
            msg = "Invalid date given, please recheck the date."
            raise errors.BadUserInputError(msg) from None
        if year is not None and not MIN_YEAR <= year <= now.astimezone(tzinfo).year:
            msg = f"The year of your birth must be between {MIN_YEAR} and the current year, please recheck it."
            raise errors.BadUserInputError(msg)
        year = year or UNKNOWN_YEAR

        confirm_embed = (
            discord
            .Embed(
                color=0xF46344,
                title="Birthday Confirmation",
                description="Do you confirm that this is the correct date/timezone for your birthday?",
            )
            .add_field(name="Date", value=birthday_fmt(month, day, year))
            .add_field(name="Timezone", value=timezone.label)
            .set_footer(
                text=(
                    "Please, double check the information! This is important because "
                    "as spam preventive measure users can only receive one congratulation per year."
                ),
            )
        )
        if not await prompts.confirm(interaction, embed=confirm_embed):
            return

        # settle down timezone questions
        saved_timezone = await self.bot.tz_manager.get_timezone(interaction.user.id)
        if saved_timezone is None:
            # no database timezone entry thus we set one
            await self.bot.tz_manager.set_timezone(interaction.user.id, timezone)
        elif saved_timezone != timezone.key:
            # different tz in input and database - let's warn the person
            # but still use birthday timezone
            text = (
                "Hey, I noticed that you just entered different timezone "
                "from the one we have in the timezone database for reminders (that you set with `/timezone set`). "
                "I did not change anything right now, but if you need to change "
                "your timezone for stuff like reminders then use `/timezone set` again."
            )
            await interaction.followup.send(embed=discord.Embed(description=text), ephemeral=True)

        # if the birthday is today, the date is today and the timer expires right away: it's celebrated immediately
        birthday_date = next_birthday_date(month, day, on_or_after=now.astimezone(tzinfo).date())
        expires_at = start_of_day(birthday_date, tzinfo)

        data: BirthdayTimerData = {"user_id": interaction.user.id, "year": year, "month": month, "day": day}
        # clear the previous birthday data before adding a new one
        await self.bot.timers.delete_by_kwargs("birthday", user_id=interaction.user.id)
        await self.bot.timers.create(
            event="birthday",
            expires_at=expires_at,
            timezone=timezone.key,
            data=data,
        )

        embed = (
            discord
            .Embed(color=interaction.user.color, title="Your birthday is successfully set")
            .add_field(name="Date", value=birthday_fmt(month, day, year))
            .add_field(name="Timezone", value=timezone.label)
            .add_field(name="Next congratulations incoming", value=clock.discord(expires_at, "R"))
            .set_footer(text="Important! By submitting this information you agree it can be shown to anyone.")
        )
        # `confirm` has used up the initial response
        await interaction.followup.send(embed=embed)

    @birthday_group.command(name="remove")
    async def birthday_remove(self, interaction: Interaction) -> None:
        """Remove your birthday data and stop getting congratulations."""
        deleted = await self.bot.timers.delete_by_kwargs("birthday", user_id=interaction.user.id)
        if not deleted:
            embed = discord.Embed(
                color=const.Palette.red_500,
                description="You don't have a birthday set.",
            ).set_author(name="NotFound")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            color=interaction.user.color,
            description="Your birthday is successfully removed from the bot database",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @birthday_group.command(name="check")
    async def birthday_check(self, interaction: Interaction, member: discord.Member | None = None) -> None:
        """Check your or somebody's birthday in database.

        Parameters
        ----------
        member
            Member of the server. If not specified - it will show your birthday.
        """
        if member is None:
            assert isinstance(interaction.user, discord.Member)
            member = interaction.user

        timer: Timer[BirthdayTimerData] | None = await self.bot.timers.get_by_kwargs("birthday", user_id=member.id)

        embed = discord.Embed(color=member.color)
        embed.set_author(name=f"{member.display_name}'s birthday status", icon_url=member.display_avatar.url)
        if timer is None:
            embed.description = "It's not set yet."
        else:
            month, day = month_and_day(timer)
            embed.add_field(name="Date", value=birthday_fmt(month, day, timer.data["year"]))
            embed.add_field(name="Timezone", value=timer.timezone)
        await interaction.response.send_message(embed=embed)

    @birthday_group.command(name="list")
    async def birthday_list(self, interaction: Interaction) -> None:
        """Show list of birthdays in this server."""
        guild = self.bot.community

        timers: list[Timer[BirthdayTimerData]] = await self.bot.timers.fetch_by_kwargs("birthday")

        birthdays: list[tuple[int, int, int, str, discord.Member]] = []
        for timer in timers:
            member = guild.get_member(timer.data["user_id"])
            if member is not None:
                month, day = month_and_day(timer)
                birthdays.append((month, day, timer.data["year"], timer.timezone, member))

        # the calendar order, regardless of the year (and of the timers' UTC moments, which depend on the timezone)
        birthdays.sort(key=operator.itemgetter(slice(2)))
        entries = [
            f"{birthday_fmt(month, day, year)}, {timezone} - {member.mention}"
            for month, day, year, timezone, member in birthdays
        ]

        paginator = pages.EmbedDescriptionPaginator(
            interaction,
            entries,
            per_page=20,
            empty_description="Nobody has set their birthday yet.",
            template={
                "title": "Birthday List",
                "color": const.Palette.purple_500,
                "footer": {"text": "DD/Month/YYYY format"},
            },
        )
        await paginator.start()

    ####################################################################################################################
    # TIMERS
    ####################################################################################################################

    @commands.Cog.listener("on_birthday_timer_complete")
    async def birthday_congratulations(self, timer: Timer[BirthdayTimerData]) -> None:
        """Send birthday notifications and schedule the next ones."""
        user_id = timer.data["user_id"]
        member = self.bot.community.get_member(user_id)

        if member is None:
            # The person is not in the server now. If the bot still remembers them they might be just temporarily
            # away, so the timer continues for next year. Otherwise they are gone for good.
            query = "SELECT EXISTS (SELECT 1 FROM community_members WHERE id = $1)"
            known = await self.bot.pool.fetchval(query, user_id)
            if known:
                await self.renew_birthday_timer(timer)
            await self.bot.timers.cleanup(timer.id)
            return

        if self.BLACKLISTED_ROLE_ID and member.get_role(self.BLACKLISTED_ROLE_ID):
            # the person is blacklisted from using the bot features
            await self.bot.timers.cleanup(timer.id)
            return

        # Schedule next year first: if anything fails below, the yearly chain of the timers is not broken.
        # (And if this fails the timer is not cleaned up, so it's retried after the next restart.)
        await self.renew_birthday_timer(timer)
        try:
            await self.congratulate(member, timer)
        finally:
            # congratulations are not retried: it would send them twice
            await self.bot.timers.cleanup(timer.id)

    async def renew_birthday_timer(self, timer: Timer[BirthdayTimerData]) -> None:
        """Create the timer for the next birthday (the dates are computed in the timezone of the birthday)."""
        tzinfo = zoneinfo.ZoneInfo(timer.timezone)
        month, day = month_and_day(timer)

        # `max`: if the bot was down for a long time, the timer is not for "today": skip to the first future birthday
        today = max(timer.expires_at.astimezone(tzinfo).date(), clock.utcnow().astimezone(tzinfo).date())
        next_date = next_birthday_date(month, day, on_or_after=today + datetime.timedelta(days=1))

        data: BirthdayTimerData = {
            "user_id": timer.data["user_id"],
            "year": timer.data["year"],
            "month": month,
            "day": day,
        }
        await self.bot.timers.create(
            event="birthday",
            expires_at=start_of_day(next_date, tzinfo),
            timezone=timer.timezone,
            data=data,
        )

    async def congratulate(self, member: discord.Member, timer: Timer[BirthdayTimerData]) -> None:
        """Give the member the birthday role and congratulate them in the channel."""
        if clock.utcnow() - timer.expires_at > STALE_AFTER:
            # the bot was down during the birthday, congratulating "today" a few days later is just weird
            return

        tzinfo = zoneinfo.ZoneInfo(timer.timezone)
        month, day = month_and_day(timer)
        year = timer.data["year"]
        now_local = clock.utcnow().astimezone(tzinfo)

        role = self.birthday_role
        await member.add_roles(role)

        content = f"Chat, today is {member.mention}'s birthday ! {role.mention}"
        if year != UNKNOWN_YEAR:
            content += f"\n{member.display_name} is now {now_local.year - year} years old !"

        embed = (
            discord
            .Embed(
                color=member.color,
                title=f"CONGRATULATIONS !!! {str(const.Emoji.peepoRoseDank) * 3}",
                description=f"{random.choice(CONGRATULATION_TEXT_BANK)} {const.Emoji.DankLove}",
            )
            .set_author(name=f"Dear {member.display_name}!", icon_url=member.display_avatar.url)
            .set_thumbnail(url=member.display_avatar.url)
            .set_image(url=random.choice(GIF_URLS_BANK))
            .set_footer(text=f"Their birthday: {birthday_fmt(month, day, year)}. Timezone: {timer.timezone}.")
        )
        mentions = discord.AllowedMentions(users=[discord.Object(member.id)], roles=[discord.Object(role.id)])
        await self.birthday_channel.send(content=content, embed=embed, allowed_mentions=mentions)

        # the role stays until the end of the birthday day in the person's timezone
        remove_role_data: RemoveRoleTimerData = {"user_id": member.id}
        await self.bot.timers.create(
            event="remove_birthday_role",
            expires_at=start_of_day(now_local.date() + datetime.timedelta(days=1), tzinfo),
            timezone=timer.timezone,
            data=remove_role_data,
        )

    @commands.Cog.listener("on_remove_birthday_role_timer_complete")
    async def birthday_cleanup(self, timer: Timer[RemoveRoleTimerData]) -> None:
        """Remove @Birthday Role from people when their birthday has passed."""
        try:
            member = self.bot.community.get_member(timer.data["user_id"])
            if member is not None:
                await member.remove_roles(self.birthday_role)
        finally:
            await self.bot.timers.cleanup(timer.id)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Birthdays(bot))
