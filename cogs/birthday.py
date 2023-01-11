from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Optional, List

import datetime
import itertools
import re
import zoneinfo
from difflib import get_close_matches
from functools import lru_cache

import discord
from discord import app_commands
from discord.ext import commands, tasks
from numpy.random import choice

from .utils.pagination import EnumeratedPages
from .utils.var import Cid, Ems, Rid, Clr, Sid

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import Context


@lru_cache(maxsize=None)
def get_timezones():
    return zoneinfo.available_timezones()


gratz_bank = [
    'I hope your special day will bring you lots of happiness, love, and fun. You deserve them a lot. Enjoy!',
    'All things are sweet and bright. May you have a lovely birthday Night.',
    'Don’t ever change! Stay as amazing as you are, my friend',
    'Let’s light the candles and celebrate this special day of your life. Happy birthday.',
    'Here\'s to the sweetest and loveliest person I know. Happy birthday!',
    'Happy birthday to my best friend, the one I care about the most!',
    'Wherever your feet may take, whatever endeavor you lay hands on. It will always be successful. Happy birthday.',
    'May this special day bring you endless joy and tons of precious memories!',
    'You are very special and that’s why you need to float with lots of smiles on your lovely face. Happy birthday.',
    'It’s as simple as ABC; today makes more sense because of you, Happy birthday.',
    'Let your all the dreams to be on fire and light your birthday candles with that. Have a gorgeous birthday.',
    'May you continue to improve as a person with each passing year. Wishing you a very happy birthday.',
    'Today is the birthday of the person who is spreading joy and positivity all around. May your birthday '
    'and your life be as wonderful as you are!',
    'Happy birthday! Here’s to a bright, healthy and exciting future!',
    'The joy is in the air because your special day is here!',
    'Your birthday only comes once a year, so make sure this is the most memorable one ever and have a colorful day.',
    'Today I wish you a fun time, shared with your dear ones, and a lifelong happiness!',
    'I always wished to be a great friend like you. '
    'But there is no way to be a better friend than you in the world. Happy birthday.',
    'Wishing you a wonderful day and all the most amazing things on your Big Day!',
    'Life is tough but birthdays are smooth because I will finally have a chance to smile at you. Happy birthday.',
    'May your birthday be full of happy hours and special moments to remember for a long long time!',
    'Soon you’re going to start a new year of your life and '
    'I hope this coming year will bring every success you deserve. Happy birthday.',
    'Wishing you a memorable day and an adventurous year, Happy birthday',
    'Hope your birthday is as wonderful and extraordinary as you are.',
    'I wish you to enjoy your special day, relax and let yourself be spoiled, you deserve it!',
    'I wish you to have a wonderful time on your Day!',
    'I wish that life brings you a beautiful surprise for every candle on your bday cake!',
    "Hugging you don't need any reason but, if there is a reason, more than one hug is a norm. Happy Birthday!",
    'I wish you a day filled with great fun and a year filled with true happiness!',
    'Let yourself do everything that you like most in life, may your Big Day be cheerful and happy!',
    'Wishing you the abundance of fun and glory, Happy Birthday!',
    'May this day be so happy that smile never fades away from your face.',
    'On your birthday friends wish you many things, but I will wish you only two: always and never. '
    'Never feel blue and always be happy!',
    'May the dream that means most to you, start coming true this year. Happy Bday!',
    'May you enjoy your special day to the fullest extent, buddy!',
    'With you, it is always about bringing in fun, in more ways than one, come rain come sun, just fun. '
    'Happy Birthday!',
    'May your birthday mark the beginning of a wonderful period of time in your life!',
    'My dear friend, may your special day be full of beautiful, magical and unforgettable moments!',
    'Happy birthday, gorgeous! You are another year older and I just can’t see it. Have a blast! '
    'Wishing you the best of the best!',
    'Wishing you greatest birthday ever, full of love and joy from the moment you open your eyes in the morning '
    'until you sleep for the night.'
]


def get_congratulation_text():
    return f'{choice(gratz_bank)} {Ems.peepoHappyDank}'


def bdate_str(bdate, num_mod=False):
    fmt = '%d/%B' if bdate.year == 1900 else '%d/%B/%Y'
    if num_mod:
        fmt = '%d/%m' if bdate.year == 1900 else '%d/%m/%Y'
    return bdate.strftime(fmt)


class SetBirthdayFlags(commands.FlagConverter, case_insensitive=True):
    day: commands.Range[int, 1, 31]
    month: Literal[
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    year: Optional[commands.Range[int, 1970]]
    timezone: Optional[str]


class Birthday(commands.Cog):
    """Set your birthday and get congratulations from the bot.

    There is a special role in Eileen's server \
    which on your birthday gives you a priority in the members list and makes the bot \
    congratulate you.
    """
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.peepoHappyDank)

    def cog_load(self) -> None:
        self.check_birthdays.start()

    def cog_unload(self) -> None:
        self.check_birthdays.cancel()

    @commands.hybrid_group()
    async def birthday(self, ctx: Context):
        """Group command about birthdays, for actual commands use it together with subcommands"""
        await ctx.scnf()

    async def timezone_autocomplete(self, _ntr: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        all_timezones = list(get_timezones())
        all_timezones += [f'GMT{sign}{h}:00' for sign, h in itertools.product(['-', '+'], range(0, 13))]
        # lazy monkey patch
        all_timezones += [
            f'GMT{i}'
            for i in [
                '+13:00', '+14:00', '+12:45', '+9:30', '+5:30', '-3:30', '+5:45', '+6:30', '+8:45', '+10:30', '+3:30',
                '-9:30',
            ]
        ]

        precise_match = [x for x in all_timezones if current.lower().startswith(x.lower())]
        close_match = get_close_matches(current, all_timezones, n=25, cutoff=0)

        return_list = list(dict.fromkeys(precise_match + close_match))
        return [app_commands.Choice(name=n, value=n) for n in return_list][:25]

    @birthday.command(
        name='set',
        aliases=['edit'],
        description='Set your birthday',
        usage='day: <day> month: <month as word> year: [year] timezone: [timezone]'
    )
    @app_commands.describe(
        day='Day', month='Month', year='Year',
        timezone='formats: `GMT+1:00`, `Europe/Paris` or `Etc/GMT-1` (sign is inverted for Etc/GMT).'
    )
    @app_commands.autocomplete(timezone=timezone_autocomplete)  # type: ignore
    async def set(self, ctx: Context, *, bdate_flags: SetBirthdayFlags):
        """Set your birthday.

        Timezone can be set in `GMT+-H:MM` format or standard IANA name like
        `Europe/Paris` or `Etc/GMT-1` (remember sign is inverted for Etc).
        """
        def get_dtime() -> datetime:
            if bdate_flags.year:
                fmt, string = '%d/%B/%Y', f'{bdate_flags.day}/{bdate_flags.month}/{bdate_flags.year}'
            else:
                fmt, string = '%d/%B', f'{bdate_flags.day}/{bdate_flags.month}'
            try:
                return datetime.datetime.strptime(string, fmt)
            except ValueError:
                raise commands.BadArgument(
                    "Invalid date given, please recheck the date."
                )

        dmy_dtime = get_dtime()

        def get_str_timezone(str_tzone: str) -> str:
            if re_zone := re.match(r'^GMT([-+]\d+:\d+)$', str_tzone, re.IGNORECASE):
                return re_zone.group(0)
            try:
                return zoneinfo.ZoneInfo(str_tzone).key
            except zoneinfo.ZoneInfoNotFoundError:
                raise commands.BadArgument(
                    'Could not recognize `timezone` from the input. \n\n'
                    'Please, use `GMT+H:MM` format or standard IANA format, i.e. `Europe/Paris` or '
                    '`Etc/GMT-1` (remember sign is inverted for `Etc/GMT-+` timezones!).\n\n'
                    'I insist that you should be using suggestions from autocomplete for `timezone` argument in '
                    '`/birthday set` slash command to ease your choice. '
                    'You can also check [TimeZonePicker](https://kevinnovak.github.io/Time-Zone-Picker/) or '
                    '[WikiPage](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) `TZ database name` column'
                )

        tz_for_db = None
        if bdate_flags.timezone:
            tz_for_db = get_str_timezone(bdate_flags.timezone)

        query = 'UPDATE users SET bdate=$1, tzone=$2 WHERE users.id=$3;'
        await self.bot.pool.execute(query, dmy_dtime, tz_for_db, ctx.author.id)
        e = discord.Embed(colour=Clr.prpl, title='Your birthday is successfully set')
        e.description = f'Date: {bdate_str(dmy_dtime)}\nTimezone: {tz_for_db}'
        e.set_footer(text='Important! By submitting this information you agree it can be shown to anyone.')
        await ctx.reply(embed=e)

    @birthday.command(aliases=['del'])
    async def delete(self, ctx: Context):
        """Delete your birthday data and stop getting congratulations"""
        query = 'UPDATE users SET bdate=$1 WHERE users.id=$2;'
        await self.bot.pool.execute(query, None, ctx.author.id)
        await ctx.reply("Your birthday is successfully deleted", ephemeral=True)

    @birthday.command(usage='[member=you]')
    @app_commands.describe(member='Member of the server or you if not specified')
    async def check(self, ctx: Context, member: Optional[discord.Member]):
        """Check your or somebody's birthday in database"""
        member = member or ctx.message.author
        query = 'SELECT bdate, tzone FROM users WHERE users.id=$1'
        row = await self.bot.pool.fetchrow(query, member.id)

        e = discord.Embed(colour=Clr.prpl)
        e.set_author(name=f'{member.display_name}\'s birthday status', icon_url=member.display_avatar.url)
        if row.bdate is None:
            e.description = f'It\'s not set yet.'
        else:
            e.description = f"Date: {bdate_str(row.bdate)}\nTimezone: {row.tzone}"
        await ctx.reply(embed=e)

    @tasks.loop(hours=1)
    async def check_birthdays(self):
        query = 'SELECT id, bdate, tzone FROM users WHERE bdate IS NOT NULL'
        rows = await self.bot.pool.fetch(query)

        for row in rows:
            bdate: datetime = row.bdate

            if row.tzone:
                if re_zone := re.match(r'^GMT([-+]\d+:\d+)$', row.tzone, re.IGNORECASE):
                    split = re_zone.group(1).split(':')
                    tzone_seconds = 3600 * int(split[0]) + 60 * int(split[1])
                    tzone_offset = datetime.timedelta(seconds=tzone_seconds)
                else:
                    tzone_offset = datetime.datetime.now(zoneinfo.ZoneInfo(row.tzone)).utcoffset()
            else:
                tzone_offset = datetime.timedelta(seconds=0)

            now_date = datetime.datetime.now(datetime.timezone.utc) + tzone_offset
            guild = self.bot.get_guild(Sid.alu)
            bperson = guild.get_member(row.id)
            if bperson is None:
                continue

            bday_rl = guild.get_role(Rid.bday)
            if now_date.month == bdate.month and now_date.day == bdate.day:
                if bday_rl not in bperson.roles:
                    await bperson.add_roles(bday_rl)
                    answer_text = f'Chat, today is {bperson.mention}\'s birthday !'
                    if bdate.year != 1900:
                        answer_text += f'{bperson.display_name} is now {now_date.year - bdate.year} years old !'
                    e = discord.Embed(title=f'CONGRATULATIONS !!! {Ems.peepoRose * 3}', color=bperson.color)
                    e.set_footer(
                        text=(
                            f'Today is {bdate_str(bdate)}; Timezone: {row.tzone}\n'
                            f'Use `$help birthday` to set up your birthday\nWith love, {guild.me.display_name}'
                        )
                    )
                    e.set_image(url=bperson.display_avatar.url)
                    e.add_field(name=f'Dear {bperson.display_name} !', inline=False, value=get_congratulation_text())
                    await self.bot.get_channel(Cid.bday_notifs).send(content=answer_text, embed=e)
            else:
                if bday_rl in bperson.roles:
                    await bperson.remove_roles(bday_rl)

    @check_birthdays.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @check_birthdays.error
    async def check_birthdays_error(self, error):
        await self.bot.send_traceback(error, where='Birthdays check')
        # self.dotafeed.restart()

    @birthday.command(name='list', hidden=True)
    async def birthday_list(self, ctx: Context):
        """Show list of birthdays in this server"""
        guild = self.bot.get_guild(Sid.alu)

        query = """ SELECT id, bdate, tzone
                    FROM users 
                    WHERE bdate IS NOT NULL 
                    ORDER BY extract(MONTH FROM bdate), extract(DAY FROM bdate);
                """
        rows = await self.bot.pool.fetch(query)

        string_list = []
        for row in rows:
            bperson = guild.get_member(row.id)
            if bperson is not None:
                string_list.append(
                    f"{bdate_str(row.bdate, num_mod=True)}"
                    f"{f', {row.tzone}' if row.tzone else ''} -"
                    f" **{bperson.mention}**"
                )

        pgs = EnumeratedPages(
            ctx,
            entries=string_list,
            per_page=20,
            title='Birthday List',
            colour=Clr.prpl,
            footer_text=f'DD/MM/YYYY format | With love, {guild.me.display_name}'
        )
        await pgs.start()


async def setup(bot: AluBot):
    await bot.add_cog(Birthday(bot))
