from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, Member, app_commands
from discord.ext import commands, tasks

from utils import database as db
from utils.var import *

from datetime import datetime, timedelta, timezone
from numpy.random import choice
from sqlalchemy import extract

if TYPE_CHECKING:
    from utils.context import Context


def get_congratulation_text():
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
        'Today is the birthday of the person who is spreading joy and positivity all around. May your birthday and your life be as wonderful as you are!',
        'Happy birthday! Here’s to a bright, healthy and exciting future!',
        'The joy is in the air because your special day is here!',
        'Your birthday only comes once a year, so make sure this is the most memorable one ever and have a colorful day.',
        'Today I wish you a fun time, shared with your dear ones, and a lifelong happiness!',
        'I always wished to be a great friend like you. But there is no way to be a better friend than you in the world. Happy birthday.',
        'Wishing you a wonderful day and all the most amazing things on your Big Day!',
        'Life is tough but birthdays are smooth because I will finally have a chance to smile at you. Happy birthday.',
        'May your birthday be full of happy hours and special moments to remember for a long long time!',
        'Soon you’re going to start a new year of your life and I hope this coming year will bring every success you deserve. Happy birthday.',
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
        'On your birthday friends wish you many things, but I will wish you only two: always and never. Never feel blue and always be happy!',
        'May the dream that means most to you, start coming true this year. Happy Bday!',
        'May you enjoy your special day to the fullest extent, buddy!',
        'With you, it is always about bringing in fun, in more ways than one, come rain come sun, just fun. Happy Birthday!',
        'May your birthday mark the beginning of a wonderful period of time in your life!',
        'My dear friend, may your special day be full of beautiful, magical and unforgettable moments!',
        'Happy birthday, gorgeous! You are another year older and I just can’t see it. Have a blast! Wishing you the best of the best!',
        'Wishing you greatest birthday ever, full of love and joy from the moment you open your eyes in the morning until you sleep for the night.'
    ]
    congratulation_text = choice(gratz_bank)
    return f'{congratulation_text} {Ems.peepoHappyDank}'


def bdate_str(bdate, num_mod=False):
    fmt = '%d/%B' if bdate.year == 1900 else '%d/%B/%Y'
    if num_mod:
        fmt = '%d/%m' if bdate.year == 1900 else '%d/%m/%Y'
    return bdate.strftime(fmt)


class Birthday(commands.Cog):
    """
    Set your birthday and get congratulations from the bot.

    There is a special role in Irene's server \
    which on your birthday gives you a priority in the members list and makes the bot \
    congratulate you.
    """
    def __init__(self, bot):
        self.bot = bot
        self.check_birthdays.start()
        self.help_emote = Ems.peepoHappyDank

    @commands.hybrid_group()
    async def birthday(self, ctx: Context):
        """Group command about birthdays, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @birthday.command(
        name='set',
        brief=Ems.slash,
        aliases=['edit'],
        description='Set your birthday'
    )
    @app_commands.describe(date='Your birthday date in "DD/MM" or "DD/MM/YYYY" format')
    async def set(self, ctx: Context, *, date: str):
        """Set your birthday. Please send `*your_birthday*` in "DD/MM" or in "DD/MM/YYYY" format.\
        If you choose the latter format, the bot will mention your age in congratulation text too;"""
        def get_dtime(text):
            for fmt in ('%d/%m/%Y', '%d/%m'):
                try:
                    return datetime.strptime(text, fmt)
                except ValueError:
                    pass
            return None
        if (dmy_dtime := get_dtime(date)) is not None:
            db.set_value(db.m, ctx.author.id, bdate=dmy_dtime)
            await ctx.reply(f"Your birthday is successfully set to {bdate_str(dmy_dtime)}")
        else:
            await ctx.reply(
                "Invalid date format, please use dd/mm/YYYY or dd/mm date format, ie. `$birthday set 26/02/1802`")

    @birthday.command(
        name='delete',
        brief=Ems.slash,
        help=f'Delete your birthday and stop getting congratulations from the bot in {cmntn(Cid.bday_notifs)};',
        aliases=['del'],
        description='Delete your birthday data'
    )
    async def delete(self, ctx: Context):
        """read above"""
        db.set_value(db.m, ctx.author.id, bdate=None)
        await ctx.reply("Your birthday is successfully deleted")

    @birthday.command(
        name='timezone',
        brief=Ems.slash,
        description='Set your timezone for birthday'
    )
    @app_commands.describe(timezone='Timezone in `float` format, ie. `-5.5` GMT -5:30 timezone')
    async def timezone(self, ctx: Context, timezone: float):
        """
        By default the bot congratulates you when your bday comes live in GMT+0 timezone. \
        This subcommand is made for adjusting that. \
        Timezone should be given as an integer or as a decimal fraction relative to GMT. \
        Usage example: `$birthday timezone -5.5` for GMT -5:30 timezone
        """
        if -13 < timezone < 13:
            db.set_value(db.m, ctx.author.id, timezone=timezone)
            await ctx.reply(f"Your timezone is successfully set to GMT {timezone:+.1f}")
        else:
            await ctx.reply("Invalid timezone value. Error id #6. Aborting...")

    @birthday.command(
        name='check',
        brief=Ems.slash,
        usage='[member=you]',
        description='Set your timezone for birthday'
    )
    @app_commands.describe(member='Member of the server or you if not specified')
    async def check(self, ctx: Context, member: Member = None):  # type: ignore
        """Check member's birthday in database"""
        member = member or ctx.message.author
        user = db.session.query(db.m).filter_by(id=member.id).first()
        bdate, tzone = user.bdate, user.timezone
        if bdate is None:
            ans = f'It seems {member.display_name}\'s hasn\'t set birthday yet.'
        else:
            ans = f'{member.display_name}\'s birthday is set to {bdate_str(bdate)} and timezone is GMT {tzone:+.1f}'
        await ctx.reply(content=ans)

    @tasks.loop(hours=1)
    async def check_birthdays(self):
        for row in db.session.query(db.m).filter(db.m.bdate.isnot(None)):  # type: ignore
            now_date = datetime.now(timezone.utc) + timedelta(hours=float(row.timezone))
            guild = self.bot.get_guild(Sid.alu)
            bperson = guild.get_member(row.id)
            if bperson is None:
                continue
            bday_rl = guild.get_role(Rid.bday)
            if now_date.month == row.bdate.month and now_date.day == row.bdate.day:
                if bday_rl not in bperson.roles:
                    await bperson.add_roles(bday_rl)
                    answer_text = f'Chat, today is {bperson.mention}\'s birthday !'
                    if row.bdate.year != 1900:
                        answer_text += f'{bperson.display_name} is now {now_date.year - row.bdate.year} years old !'
                    embed = Embed(
                        color=bperson.color,
                        title=f'CONGRATULATIONS !!! {Ems.peepoRose * 3}'
                    ).set_footer(
                        text=
                        f'Today is {bdate_str(row.bdate)}; Timezone: GMT {row.timezone:+.1f}\n'
                        f'Use `$help birthday` to set up your birthday\nWith love, {guild.me.display_name}'
                    ).set_image(
                        url=bperson.display_avatar.url
                    ).add_field(
                        name=f'Dear {bperson.display_name} !',
                        inline=False,
                        value=get_congratulation_text()
                    )
                    await guild.get_channel(Cid.bday_notifs).send(content=answer_text, embed=embed)
            else:
                if bday_rl in bperson.roles:
                    await bperson.remove_roles(bday_rl)

    @check_birthdays.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @commands.is_owner()
    @commands.command(hidden=True)
    async def birthdaylist(self, ctx: Context):
        """
        Show list of birthdays in this server
        """
        guild = self.bot.get_guild(Sid.alu)
        text = ''
        for row in db.session.query(db.m).filter(db.m.bdate.isnot(None)).order_by(  # type: ignore
                extract('month', db.m.bdate), extract('day', db.m.bdate)):
            bperson = guild.get_member(row.id)
            if bperson is not None:
                text += f'{bdate_str(row.bdate, num_mod=True)}, GMT {row.timezone:+.1f} - **{bperson.mention}**\n'

        embed = Embed(
            color=Clr.prpl,
            title='Birthday list',
            description=text
        ).set_footer(
            text=f'With love, {guild.me.display_name}'
        )
        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(Birthday(bot))
