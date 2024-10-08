from __future__ import annotations

import datetime
import random
import zoneinfo
from typing import TYPE_CHECKING, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands

from utils import checks, const, converters, formats, pages

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot, AluGuildContext, Timer, TimerRecord


class BirthdayTimerData(TypedDict):
    user_id: int
    year: int


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
    "Today is the birthday of the person who is spreading joy and positivity all around. May your birthday "
    "and your life be as wonderful as you are!",
    "Happy birthday! Here's to a bright, healthy and exciting future!",
    "The joy is in the air because your special day is here!",
    "Your birthday only comes once a year, so make sure this is the most memorable one ever and have a colorful day.",
    "Today I wish you a fun time, shared with your dear ones, and a lifelong happiness!",
    "I always wished to be a great friend like you. "
    "But there is no way to be a better friend than you in the world. Happy birthday.",
    "Wishing you a wonderful day and all the most amazing things on your Big Day!",
    "Life is tough but birthdays are smooth because I will finally have a chance to smile at you. Happy birthday.",
    "May your birthday be full of happy hours and special moments to remember for a long long time!",
    "Soon you're going to start a new year of your life and "
    "I hope this coming year will bring every success you deserve. Happy birthday.",
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
    "With you, it is always about bringing in fun, in more ways than one, come rain come sun, just fun. "
    "Happy Birthday!",
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


def birthday_fmt(birthday_date: datetime.datetime) -> str:
    """Format a date to show in the bot's embeds.

    Example:
    -------
    Output: "28/August/2025"

    """
    fmt = "%d/%B" if birthday_date.year == 1900 else "%d/%B/%Y"
    return birthday_date.strftime(fmt)


class Birthday(CommunityCog, emote=const.Emote.peepoHappyDank):
    """Set your birthday and get congratulations from the bot.

    There is a special role in Eileen's server \
    which on your birthday gives you a priority in the members list and makes the bot \
    congratulate you.
    """

    @override
    async def cog_load(self) -> None:
        self.bot.initialize_tz_manager()

    @discord.utils.cached_property
    def birthday_channel(self) -> discord.TextChannel:
        """The channel where birthday notifications are sent."""
        channel = self.community.logs if self.bot.test else self.community.bday_notifs
        return channel

    @checks.hybrid.is_community()
    @commands.hybrid_group()
    async def birthday(self, ctx: AluGuildContext) -> None:
        """Commands about managing your birthday data."""
        await ctx.send_help(ctx.command)

    @birthday.command(
        name="set",
        aliases=["edit"],
        description="Set your birthday",
        usage="day: <day> month: <month as word> year: [year] timezone: [timezone]",
    )
    async def birthday_set(self, ctx: AluGuildContext, *, birthday: converters.DateTimezonePicker) -> None:
        """Set your birthday."""
        dt = birthday.verify_date()

        confirm_embed = (
            discord.Embed(
                colour=0xF46344,
                title="Birthday Confirmation",
                description="Do you confirm that this is the correct date/timezone for your birthday?",
            )
            .add_field(name="Date", value=birthday_fmt(dt))
            .add_field(name="Timezone", value=birthday.timezone.label)
            .set_footer(
                text=(
                    "Please, double check the information! This is important because "
                    "as spam preventive measure users can only receive one congratulation per year."
                )
            )
        )
        if not await self.bot.disambiguator.confirm(ctx, embed=confirm_embed):
            return

        # settle down timezone questions
        zone = await ctx.bot.tz_manager.get_timezone(ctx.author.id)
        if not zone:
            # no database timezone entry thus we set one
            await self.bot.tz_manager.set_timezone(ctx.author.id, birthday.timezone)
        elif birthday.timezone.key != zone:
            # different tz in input and database - let's warn the person
            # but still use birthday timezone
            text = (
                "Hey, I noticed that you just entered different timezone "
                "from the one we have in the timezone database for reminders (that you set with `/timezone set`). "
                "I did not change anything right now, but if you need to change "
                "your timezone for stuff like reminders then use `/timezone set` again.",
            )
            e = discord.Embed(description=text)
            await ctx.reply(embed=e, ephemeral=True)

        data: BirthdayTimerData = {
            "user_id": ctx.author.id,
            "year": birthday.year,
        }

        end_of_today = datetime.datetime.now(birthday.timezone.to_tzinfo()).replace(hour=0, minute=0, second=0)
        expires_at = dt.replace(hour=0, minute=0, second=1, year=end_of_today.year)
        if expires_at < end_of_today:
            # the birthday already happened this year
            expires_at = dt.replace(year=end_of_today.year + 1)

        # clear the previous birthday data before adding a new one
        await self.remove_birthday_worker(ctx.author.id)
        await self.bot.create_timer(
            event="birthday",
            expires_at=expires_at,
            timezone=birthday.timezone.key,
            data=data,
        )

        embed = (
            discord.Embed(colour=ctx.author.colour, title="Your birthday is successfully set")
            .add_field(name="Data", value=birthday_fmt(dt))
            .add_field(name="Timezone", value=birthday.timezone.label)
            .add_field(name="Next congratulations incoming", value=formats.format_dt(expires_at, "R"))
            .set_footer(text="Important! By submitting this information you agree it can be shown to anyone.")
        )
        await ctx.reply(embed=embed)

    async def remove_birthday_worker(self, user_id: int) -> str:
        query = """
            DELETE FROM timers
            WHERE event = 'birthday'
            AND data #>> '{user_id}' = $1;
        """
        status = await self.bot.pool.execute(query, str(user_id))

        current_timer = self.bot._current_timer
        if current_timer and current_timer.event == "timer" and current_timer.data:
            author_id = current_timer.data.get("user_id")
            if author_id == user_id:
                self.bot.rerun_the_task()

        return status

    @birthday.command(aliases=["del", "delete"])
    async def remove(self, ctx: AluGuildContext) -> None:
        """Remove your birthday data and stop getting congratulations."""
        status = await self.remove_birthday_worker(ctx.author.id)
        if status == "DELETE 0":
            embed = discord.Embed(
                colour=const.Colour.maroon,
                description="Could not delete your birthday with that ID.",
            ).set_author(name="DatabaseError")
            await ctx.reply(embed=embed)
            return

        embed = discord.Embed(
            colour=ctx.author.color,
            description="Your birthday is successfully removed from the bot database",
        )
        await ctx.reply(embed=embed, ephemeral=True)

    @birthday.command(usage="[member=you]")
    @app_commands.describe(member="Member of the server or you if not specified")
    async def check(self, ctx: AluGuildContext, member: discord.Member = commands.Author) -> None:
        """Check your or somebody's birthday in database."""
        query = """
            SELECT * FROM timers
            WHERE event = 'birthday'
            AND data #>> '{user_id}' = $1;
        """
        row: TimerRecord[BirthdayTimerData] | None = await self.bot.pool.fetchrow(query, str(member.id))

        e = discord.Embed(colour=member.color)
        e.set_author(name=f"{member.display_name}'s birthday status", icon_url=member.display_avatar.url)
        if row is None:
            e.description = "It's not set yet."
        else:
            e.add_field(name="Date", value=birthday_fmt(row.expires_at.replace(year=row.data["year"])))
            e.add_field(name="Timezone", value=row["timezone"])
        await ctx.reply(embed=e)

    @commands.Cog.listener("on_birthday_timer_complete")
    async def birthday_congratulations(self, timer: Timer[BirthdayTimerData]) -> None:
        """Send birthday notifications."""
        user_id = timer.data["user_id"]
        year = timer.data["year"]

        guild = self.community.guild

        member = guild.get_member(user_id)
        if member is None:
            # user is not in the guild anymore
            # so let's check if the user data is deleted from the database
            query = """--sql
                SELECT * FROM community_members WHERE id = $1;
            """
            user_row = await self.bot.pool.fetchrow(query, user_id)
            if user_row:
                # continue the timer for next year :D
                pass
            else:
                # don't continue the timer
                return
        else:
            # Send notification

            if self.community.blacklisted in member.roles:
                # the person is blacklisted from using the bot features.
                return

            birthday_role = self.community.birthday_role
            # if birthday_role in member.roles:
            #     # I guess the notification already happened
            #     return

            await member.add_roles(birthday_role)

            content = f"Chat, today is {member.mention}'s birthday ! {const.Role.birthday_lover}"

            now = datetime.datetime.now().astimezone(zoneinfo.ZoneInfo(timer.timezone))
            if year != 1900:
                content += f"\n{member.display_name} is now {now.year - year} years old !"

            embed = (
                discord.Embed(
                    color=member.color,
                    title=f"CONGRATULATIONS !!! {const.Emote.peepoRoseDank * 3}",
                    description=f"{random.choice(CONGRATULATION_TEXT_BANK)} {const.Emote.peepoHappyDank}",
                )
                .set_author(name=f"Dear {member.display_name}!", icon_url=member.display_avatar.url)
                .set_thumbnail(url=member.display_avatar.url)
                .set_image(url=random.choice(GIF_URLS_BANK))
                .set_footer(text=f"Their birthday: {birthday_fmt(now.replace(year=year))}. Timezone: {timer.timezone}.")
            )

            await self.birthday_channel.send(content=content, embed=embed)

            # create remove roles timer
            await self.bot.create_timer(
                event="remove_birthday_role",
                expires_at=timer.expires_at + datetime.timedelta(days=1),
                created_at=timer.created_at,
                timezone=timer.timezone,
                data=timer.data,
            )

        # create next year timer
        await self.bot.create_timer(
            event="birthday",
            expires_at=timer.expires_at.replace(year=timer.expires_at.year + 1),
            created_at=timer.created_at,
            timezone=timer.timezone,
            data=timer.data,
        )

    @commands.Cog.listener("on_remove_birthday_role_timer_complete")
    async def birthday_cleanup(self, timer: Timer[BirthdayTimerData]) -> None:
        """Remove @Birthday Role from people when their birthday has passed."""
        user_id = timer.data["user_id"]
        birthday_role = self.community.birthday_role
        guild = self.community.guild

        member = guild.get_member(user_id)
        if member is not None:
            await member.remove_roles(birthday_role)

    @birthday.command(name="list", hidden=True)
    async def birthday_list(self, ctx: AluGuildContext) -> None:
        """Show list of birthdays in this server."""
        guild = self.community.guild

        query = """
            SELECT expires_at, timezone, data FROM timers
            WHERE event = 'birthday'
            ORDER BY extract(MONTH FROM expires_at), extract(DAY FROM expires_at);
        """
        rows: list[TimerRecord[BirthdayTimerData]] = await self.bot.pool.fetch(query)

        string_list = []
        for row in rows:
            birthday_person = guild.get_member(row.data["user_id"])
            if birthday_person is not None:
                date = row.expires_at.astimezone(zoneinfo.ZoneInfo(key=row.timezone)).replace(year=row.data["year"])
                string_list.append(f"{birthday_fmt(date)}, {row.timezone} - {birthday_person.mention}")

        pgs = pages.EnumeratedPaginator(
            ctx,
            entries=string_list,
            per_page=20,
            title="Birthday List",
            colour=const.Colour.blueviolet,
            footer_text="DD/Month/YYYY format",
        )
        await pgs.start()


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Birthday(bot))
