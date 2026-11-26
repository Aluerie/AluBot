# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Birthdays."""

from __future__ import annotations

import calendar
import datetime as dt
import enum
import operator
import random
from typing import TYPE_CHECKING, Any, Final, TypedDict, override

import discord
from discord import app_commands

from core import Cog, TransformTimeZone
from shared import clock, errors, scheduler
from shared.scheduler import Job, WallTime
from utils import const, pages, prompts

if TYPE_CHECKING:
    from core import Bot, Interaction


class BirthdayData(TypedDict, closed=True):
    """Data of a birthday job; the user is the job's `user_id`, the timezone is the job's."""

    year: int | None
    month: int
    day: int


__all__ = ("Birthdays",)

MIN_YEAR = 1950
"""The earliest year of birth that can be entered."""
STALE_AFTER = dt.timedelta(days=1)
"""If the bot was down for longer than this since the birthday, congratulating "today" is pointless."""


def birthday_key(user_id: int) -> str:
    """Key of the job of the user's birthday."""
    return f"birthday:{user_id}"


def birthday_role_key(user_id: int) -> str:
    """Key of the job that takes the birthday role from the user at the end of their birthday."""
    return f"birthday-role:{user_id}"


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
    (
        "On your birthday friends wish you many things, but I will wish you only two: always and never. "
        "Never feel blue and always be happy!"
    ),
    "May the dream that means most to you, start coming true this year. Happy Bday!",
    "May you enjoy your special day to the fullest extent, buddy!",
    (
        "With you, it is always about bringing in fun, in more ways than one, come rain come sun, just fun. "
        "Happy Birthday!"
    ),
    "May your birthday mark the beginning of a wonderful period of time in your life!",
    "My dear friend, may your special day be full of beautiful, magical and unforgettable moments!",
    (
        "Happy birthday, gorgeous! You are another year older and I just can't see it. Have a blast! "
        "Wishing you the best of the best!"
    ),
    (
        "Wishing you greatest birthday ever, full of love and joy from the moment you open your eyes in the morning "
        "until you sleep for the night."
    ),
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


def birthday_fmt(month: int, day: int, year: int | None) -> str:
    """Format a date to show in the bot's embeds.

    Parameters
    ----------
    month
        Month of the birthday.
    day
        Day of the birthday.
    year
        Year of the birth. ``None`` hides it.

    Returns
    -------
    str
        Date like "28/August/2025" (or "28/August" if the year is unknown).
    """
    text = f"{day:02d}/{Month(month).name}"
    return text if year is None else f"{text}/{year}"


def birthday_in_year(month: int, day: int, year: int) -> dt.date:
    """Get the date of a birthday in the given year.

    People born on the 29th of February celebrate on the 28th of February in non-leap years.
    """
    if month == 2 and day == 29 and not calendar.isleap(year):
        day = 28
    return dt.date(year, month, day)


def next_birthday_date(month: int, day: int, *, on_or_after: dt.date) -> dt.date:
    """Get the first date of the birthday that is not earlier than `on_or_after`."""
    date = birthday_in_year(month, day, on_or_after.year)
    if date < on_or_after:
        date = birthday_in_year(month, day, on_or_after.year + 1)
    return date


def start_of_day(date: dt.date, timezone: str) -> WallTime:
    """Get the very beginning of the date on the clocks of the timezone."""
    return WallTime(dt.datetime.combine(date, dt.time()), timezone)


def next_birthday(job: Job[Any], now: dt.datetime) -> WallTime:
    """Repeat a birthday job: the next birthday after the one that just happened (and after today).

    The dates are counted on the clocks of the person's timezone, and 29th of February birthdays
    happen on the 28th in other years.
    """
    data: BirthdayData = job.data
    today = WallTime.from_aware(now, job.when.timezone).local.date()
    after = max(job.when.local.date(), today) + dt.timedelta(days=1)
    return start_of_day(next_birthday_date(data["month"], data["day"], on_or_after=after), job.when.timezone)


class Birthdays(Cog):
    """Set your birthday and get congratulations from the bot.

    There is a special role in Eileen's server
    which on your birthday gives you a priority in the members list and makes the bot
    congratulate you.
    """

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

    # --- COMMANDS -----------------------------------------------------------------------------------------------------

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
        user = interaction.user

        try:
            # the year only matters for the validity of the date, so for an unknown year pick a leap one (29 Feb)
            dt.date(year or 2000, month, day)
        except ValueError:
            msg = "Invalid date given, please recheck the date."
            raise errors.BadUserInputError(msg) from None
        if year is not None and not MIN_YEAR <= year <= now.astimezone(tzinfo).year:
            msg = f"The year of your birth must be between {MIN_YEAR} and the current year, please recheck it."
            raise errors.BadUserInputError(msg)

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

        # If the birthday is today, the job is due right away: it's celebrated immediately.
        # But only once: after a congratulation the member keeps the birthday role (and the job to remove it)
        # until the end of the day, so setting the birthday again (or removing and setting it) can't repeat it.
        congratulated_today = (
            isinstance(user, discord.Member) and user.get_role(self.birthday_role.id) is not None
        ) or await self.bot.scheduler.get_by_key(birthday_role_key(user.id)) is not None
        earliest = now.astimezone(tzinfo).date()
        if congratulated_today:
            earliest += dt.timedelta(days=1)
        birthday_date = next_birthday_date(month, day, on_or_after=earliest)

        data: BirthdayData = {"year": year, "month": month, "day": day}
        job = await self.bot.scheduler.schedule(
            "birthday",
            start_of_day(birthday_date, timezone.key),
            data=data,
            key=birthday_key(user.id),
            user_id=user.id,
            guild_id=const.Guild.community,
            on_conflict="replace",
        )

        embed = (
            discord
            .Embed(color=interaction.user.color, title="Your birthday is successfully set")
            .add_field(name="Date", value=birthday_fmt(month, day, year))
            .add_field(name="Timezone", value=timezone.label)
            .add_field(name="Next congratulations incoming", value=clock.discord(job.due_at, "R"))
            .set_footer(text="Important! By submitting this information you agree it can be shown to anyone.")
        )
        # `confirm` has used up the initial response
        await interaction.followup.send(embed=embed)

    @birthday_group.command(name="remove")
    async def birthday_remove(self, interaction: Interaction) -> None:
        """Remove your birthday data and stop getting congratulations."""
        deleted = await self.bot.scheduler.delete_by_key(birthday_key(interaction.user.id))
        if deleted is None:
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

        job: Job[BirthdayData] | None = await self.bot.scheduler.get_by_key(birthday_key(member.id))

        embed = discord.Embed(color=member.color)
        embed.set_author(name=f"{member.display_name}'s birthday status", icon_url=member.display_avatar.url)
        if job is None:
            embed.description = "It's not set yet."
        else:
            data = job.data
            embed.add_field(name="Date", value=birthday_fmt(data["month"], data["day"], data["year"]))
            embed.add_field(name="Timezone", value=job.when.timezone)
            embed.add_field(name="Next congratulations", value=clock.discord(job.due_at, "R"))
        await interaction.response.send_message(embed=embed)

    @birthday_group.command(name="list")
    async def birthday_list(self, interaction: Interaction) -> None:
        """Show list of birthdays in this server."""
        guild = self.bot.community

        jobs: list[Job[BirthdayData]] = await self.bot.scheduler.fetch("birthday")

        birthdays: list[tuple[int, int, int | None, str, discord.Member]] = []
        for job in jobs:
            member = guild.get_member(job.user_id or 0)
            if member is not None:
                data = job.data
                birthdays.append((data["month"], data["day"], data["year"], job.when.timezone, member))

        # the calendar order, regardless of the year (and of the jobs' UTC moments, which depend on the timezone)
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

    # --- JOBS ---------------------------------------------------------------------------------------------------------

    # A late birthday is skipped (congratulating "today" days later is weird), and a failed one isn't retried
    # (it could send the congratulations twice). Either way the job moves on to the next year.
    @scheduler.handler("birthday", recur=next_birthday, max_lateness=STALE_AFTER, max_attempts=1)
    async def birthday_congratulations(self, job: Job[BirthdayData]) -> scheduler.Stop | None:
        """Congratulate the member on their birthday; the job then moves on to the next year by itself."""
        user_id = job.user_id or 0
        member = self.bot.community.get_member(user_id)

        if member is None:
            # The person is not in the server now. If the bot still remembers them they might be just temporarily
            # away, so the birthday stays for next year. Otherwise they are gone for good.
            query = "SELECT EXISTS (SELECT 1 FROM community_members WHERE id = $1)"
            known = await self.bot.pool.fetchval(query, user_id)
            return None if known else scheduler.STOP

        if self.BLACKLISTED_ROLE_ID and member.get_role(self.BLACKLISTED_ROLE_ID):
            # the person is blacklisted from using the bot features
            return None

        await self.congratulate(member, job)
        return None

    async def congratulate(self, member: discord.Member, job: Job[BirthdayData]) -> None:
        """Give the member the birthday role and congratulate them in the channel."""
        timezone = job.when.timezone
        month, day, year = job.data["month"], job.data["day"], job.data["year"]
        today = WallTime.from_aware(clock.utcnow(), timezone).local.date()

        role = self.birthday_role
        await member.add_roles(role)

        content = f"Chat, today is {member.mention}'s birthday ! {role.mention}"
        if year is not None:
            content += f"\n{member.display_name} is now {today.year - year} years old !"

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
            .set_footer(text=f"Their birthday: {birthday_fmt(month, day, year)}. Timezone: {timezone}.")
        )
        mentions = discord.AllowedMentions(users=[discord.Object(member.id)], roles=[discord.Object(role.id)])
        await self.birthday_channel.send(content=content, embed=embed, allowed_mentions=mentions)

        # the role stays until the end of the birthday day in the person's timezone
        await self.bot.scheduler.schedule(
            "birthday_role",
            start_of_day(today + dt.timedelta(days=1), timezone),
            key=birthday_role_key(member.id),
            user_id=member.id,
            guild_id=const.Guild.community,
            on_conflict="replace",
        )

    @scheduler.handler("birthday_role")
    async def remove_birthday_role(self, job: Job[Any]) -> None:
        """Take the birthday role from the member when their birthday is over."""
        member = self.bot.community.get_member(job.user_id or 0)
        if member is not None:
            await member.remove_roles(self.birthday_role)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Birthdays(bot))
