from __future__ import annotations

import colorsys
import platform
import re
import socket
import warnings
from datetime import datetime, timezone, timedelta, time
from typing import TYPE_CHECKING, List, Literal, Union

from dota2 import __version__ as dota2_version
import psutil
from pyot import __version__ as pyot_version
from PIL import ImageColor, Image
from async_google_trans_new import google_translator
from dateparser.search import search_dates
from discord import __version__ as dpy_version
from discord import (
    Colour, Embed, Member, Message, Role, TextChannel,
    app_commands
)
from discord.ext import commands, tasks
# from wordcloud import WordCloud #todo: wait for a fix

from config import DISCORD_BOT_INVLINK
from .utils.checks import is_owner
from .utils.format import humanize_time
from .utils.imgtools import img_to_file
from .utils.time import format_tdR
from .utils.var import Cid, Clr, Ems, Sid, Rid, MP, MAP

if TYPE_CHECKING:
    from discord import Interaction, Guild
    from .utils.bot import AluBot
    from .utils.context import Context

# Ignore dateparser warnings regarding pytz
warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)


async def account_age_ctx_menu(ntr: Interaction, member: Member):
    """View the age of an account."""
    age = datetime.now(timezone.utc) - member.created_at
    await ntr.response.send_message(f"{member.mention} is {humanize_time(age)} old.", ephemeral=True)


async def translate_msg_ctx_menu(ntr: Interaction, message: Message):
    embed = Embed(colour=message.author.colour, title='Google Translate to English')
    if len(message.content) == 0:
        embed.description = "Sorry it seems this message doesn't have content"
    else:
        translator = google_translator()
        embed.description = await translator.translate(message.content, lang_tgt='en')
        embed.set_footer(text=f'Detected language: {(await translator.detect(message.content))[0]}')
    await ntr.response.send_message(embed=embed, ephemeral=True)


class Info(commands.Cog, name='Info'):
    """
    Commands to get some useful info
    """

    def __init__(self, bot):
        self.bot: AluBot = bot
        self.reload_info.start()
        self.help_emote = Ems.PepoG

        self.ctx_menu1 = app_commands.ContextMenu(name='Translate to English', callback=translate_msg_ctx_menu)
        self.bot.tree.add_command(self.ctx_menu1)

        self.ctx_menu2 = app_commands.ContextMenu(name='View Account Age', callback=account_age_ctx_menu)
        self.bot.tree.add_command(self.ctx_menu2)

    async def cog_unload(self) -> None:
        self.reload_info.cancel()
        self.bot.tree.remove_command(self.ctx_menu1.name, type=self.ctx_menu1.type)
        self.bot.tree.remove_command(self.ctx_menu2.name, type=self.ctx_menu2.type)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        pdates = search_dates(message.content)
        if pdates is None:
            return
        for pdate in pdates:
            if pdate[1].tzinfo is not None:
                dt = pdate[1]
                em = Embed(colour=Clr.prpl)
                em.description = \
                    f'"{pdate[0]}" in your timezone:\n {format_tdR(dt)}\n' \
                    f'{dt.tzname()} is GMT {dt.utcoffset().seconds / 3600:+.1f}, dls: {dt.dst().seconds / 3600:+.1f}'
                await message.channel.send(embed=em)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.guild.id != Sid.alu:
            return
        added_role = list(set(after.roles) - set(before.roles))
        removed_role = list(set(before.roles) - set(after.roles))

        async def give_text_list(role_id, ch_id, msg_id):
            if (added_role and added_role[0].id == role_id) or (removed_role and removed_role[0].id == role_id):
                channel = before.guild.get_channel(ch_id)
                msg = channel.get_partial_message(msg_id)
                role = before.guild.get_role(role_id)
                em = Embed(title=f'List of {role.name}', colour=Clr.prpl)
                em.description = ''.join([f'{member.mention}\n' for member in role.members])
                await msg.edit(content='', embed=em)

        await give_text_list(Rid.bots, Cid.bot_spam, 959982214827892737)
        await give_text_list(Rid.nsfwbots, Cid.nsfw_bob_spam, 959982171492323388)

    @commands.hybrid_command(
        name='gmt',
        aliases=['utc'],
        description="Show GMT(UTC) time"
    )
    async def gmt(self, ctx):
        """Show GMT(UTC) time ;"""
        now_time = datetime.now(timezone.utc).strftime("%H:%M:%S")
        now_date = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        em = Embed(colour=Clr.prpl, title='GMT(Greenwich Mean Time)')
        em.set_footer(
            text=f'GMT is the same as UTC (Universal Time Coordinated)\nWith love, {ctx.guild.me.display_name}'
        )
        em.add_field(name='Time:', value=now_time)
        em.add_field(name='Date:', value=now_date)
        await ctx.reply(embed=em)

    @commands.hybrid_command(
        name='role',
        aliases=['members', 'roleinfo'],
        description="View info about selected role"
    )
    @app_commands.describe(role='Choose role to get info about')
    async def roleinfo(self, ctx, *, role: Role):
        """View info about selected role"""
        em = Embed(title="Role information", colour=role.colour)
        em.description = '\n'.join([f'{counter} {m.mention}' for counter, m in enumerate(role.members, start=1)])
        # TODO: this embed will be more than 6000 symbols
        await ctx.reply(embed=em)

    @tasks.loop(count=1)
    async def reload_info(self):
        em = Embed(colour=Clr.prpl, description=f'Logged in as {self.bot.user}')
        await self.bot.get_channel(Cid.spam_me).send(embed=em)
        self.bot.help_command.cog = self  # show help command in there
        if not self.bot.test:
            # em.set_author(name='Finished updating/rebooting')
            await self.bot.get_channel(Cid.bot_spam).send(embed=em)

    @reload_info.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(
        name='translate',
        description='Translate text to English, auto-detects source language'
    )
    @app_commands.describe(text="Enter text to translate")
    async def translate(self, ctx, *, text: str):
        """
        Translate text into English using Google Translate, auto-detects source language.
        """
        translator = google_translator()
        em = Embed(
            colour=ctx.author.colour,
            title='Google Translate to English',
            description=await translator.translate(text, lang_tgt='en')
        ).set_footer(
            text=f'Detected language: {(await translator.detect(text))[0]}'
        )
        await ctx.reply(embed=em)

    colour_info = \
        'The bot supports the following string formats:\n' \
        '• Hexadecimal specifiers: `#rgb`, `#rgba`, `#rrggbb` or `#rrggbbaa`\n' \
        '• RGB: `rgb(red, green, blue)` where the colour values are integers or percentages\n' \
        '• Hue-Saturation-Lightness (HSL): `hsl(hue, saturation%, lightness%)`\n' \
        '• Hue-Saturation-Value (HSV): `hsv(hue, saturation%, value%)`\n' \
        '• Common HTML color names: `red`, `Blue`\n' \
        '• Extra: MaterialUI Google Palette: `mu(colour_name, shade)`\n' \
        '• Extra: MateriaAccentlUI Google Palette: `mu(colour_name, shade)`\n' \
        '• Last but not least: `prpl` for favourite Aluerie\'s colour '

    @commands.hybrid_command(
        name='colour',
        description="Get info about colour",
        aliases=['color'],
        usage='<formatted_colour_string>',
        help=f'Get info about colour in specified <formatted_colour_string>.\n{colour_info}'
    )
    @app_commands.describe(colour_arg='Colour in any of supported formats')
    async def colour(self, ctx, *, colour_arg: str):
        """
        Read above.
        """
        if colour_arg == 'prpl':
            colour_arg = '#9678B6'

        m = re.match(
            r"mu\(\s*([a-zA-Z]+)\s*,\s*(\d+)\s*\)$", colour_arg
        )
        if m:
            colour_arg = hex(MP.colors_dict[m.group(1)][int(m.group(2))]).replace('0x', '#')

        m = re.match(
            r"mua\(\s*([a-zA-Z]+)\s*,\s*(\d+)\s*\)$", colour_arg
        )
        if m:
            colour_arg = hex(MAP.colors_dict[m.group(1)][int(m.group(2))]).replace('0x', '#')

        rgb = ImageColor.getcolor(colour_arg, "RGB")

        def rgb2hex(r, g, b):
            return "#{:02x}{:02x}{:02x}".format(r, g, b)

        img = Image.new('RGB', (300, 300), rgb)
        file = img_to_file(img, filename='colour.png')
        em = Embed(color=Colour.from_rgb(*rgb), title='Colour info')
        em.description = (
            f'Hex triplet: `{rgb2hex(*rgb)}`\n' +
            'RGB: `({}, {}, {})`\n'.format(*rgb) +
            'HSV: `({:.2f}, {:.2f}, {})`\n'.format(*colorsys.rgb_to_hsv(*rgb)) +
            'HLS: `({:.2f}, {}, {:.2f})`\n'.format(*colorsys.rgb_to_hls(*rgb))
        )
        em.set_thumbnail(url=f'attachment://{file.filename}')
        await ctx.reply(embed=em, file=file)

    @colour.autocomplete('colour_arg')
    async def colour_callback(
            self,
            _: Interaction,
            current: str
    ) -> List[app_commands.Choice[str]]:
        colours = [
            'prpl',
            'rgb(',
            'hsl(',
            'hsv(',
            'mu(',
            'mua('
        ] + list(ImageColor.colormap.keys())
        return [
            app_commands.Choice(name=clr, value=clr)
            for clr in colours if current.lower() in clr.lower()
        ][:25]

    @colour.error
    async def colour_error(self, ctx, error):
        if isinstance(error, (
                commands.HybridCommandError,
                commands.CommandInvokeError,
                app_commands.CommandInvokeError
        )):
            error = error.original
            if isinstance(error, (commands.CommandInvokeError, app_commands.CommandInvokeError)):
                error = error.original

        if isinstance(error, (ValueError, KeyError)):
            ctx.error_handled = True
            em = Embed(
                colour=Clr.error,
                title='Wrong colour format',
                url='https://pillow.readthedocs.io/en/stable/reference/ImageColor.html',
                description=self.colour_info
            ).set_author(
                name='WrongColourFormat'
            )
            await ctx.reply(embed=em, ephemeral=True)

    @commands.hybrid_group()
    async def info(self, ctx: Context):
        """Group command about Info, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @info.command(
        name='sysinfo',
        description='Get system info about machine currently hosting the bot',
        aliases=['systeminfo']
    )
    async def sysinfo(self, ctx: Context):
        """Get system info about machine currently hosting the bot"""
        url = 'https://ipinfo.io/json'
        async with self.bot.session.get(url) as resp:
            data = await resp.json()

        embed = Embed(
            colour=Clr.prpl,
            title="Bot Host Machine System Info",
            description=(
                f'● Hostname: {socket.gethostname()}\n'
                f'● Machine: {platform.machine()}\n'
                f'● Platform: {platform.platform()}\n'
                f'● System: `{platform.system()}` release: `{platform.release()}`\n'
                f'● Version: `{platform.version()}`\n'
                f'● Processor: {platform.processor()}\n'
            ),
        ).add_field(
            name='Current % | max values',
            value=(
                f'● CPU usage: \n{psutil.cpu_percent()}% | {psutil.cpu_freq().current / 1000:.1f}GHz\n'
                f'● RAM usage: \n{psutil.virtual_memory().percent}% | '
                f'{str(round(psutil.virtual_memory().total / (1024.0 ** 3))) + " GB"}\n'
                f'● Disk usage: \n{(du := psutil.disk_usage("/")).percent} % | '
                f'{du.used / (1024 ** 3):.1f}GB/{du.total / (1024 ** 3):.1f}GB'
            )
        ).add_field(
            name='Python Versions',
            value=(
                f'● Python: {platform.python_version()}\n'
                f'● discord.py {dpy_version}\n'
                f'● dota2 {dota2_version}\n'
                f'● Pyot {pyot_version}\n'
            )
        ).set_footer(
            text=f'AluBot is a copyright 2020-{datetime.now().year} of {self.bot.owner.name}'
        )
        if not self.bot.test:
            embed.add_field(
                name="Location judging by IP",
                value=f"· {data['country']} {data['region']} {data['city']}"
            )
        await ctx.reply(embed=embed)

    @info.command(
        name='stats',
        description='Summary stats for the bot'
    )
    async def stats(self, ctx):
        """Summary stats for the bot ;"""
        em = Embed(
            colour=Clr.prpl,
            title='Summary bot stats'
        ).set_thumbnail(
            url=self.bot.user.avatar.url
        ).add_field(
            name="Server Count",
            value=str(len(self.bot.guilds))
        ).add_field(
            name="User Count",
            value=str(len(self.bot.users))
        ).add_field(
            name="Ping",
            value=f"{self.bot.latency * 1000:.2f}ms"
        ).add_field(
            name='Uptime',
            value=humanize_time(datetime.now(timezone.utc) - self.bot.launch_time, full=False)
        )
        await ctx.reply(embed=em)

    @is_owner()
    @commands.command(aliases=['invitelink', 'invite_link'], hidden=True)
    async def invite(self, ctx):
        """Show invite link for the bot."""
        em = Embed(
            color=Clr.prpl,
            description=DISCORD_BOT_INVLINK
        )
        await ctx.reply(embed=em)

    @staticmethod
    def guild_embed(guild: Guild, event: Literal['join', 'remove']):
        e_dict = {
            'join': {
                'clr': MP.green(shade=500),
                'word': 'joined'
            },
            'remove': {
                'clr': MP.red(shade=500),
                'word': 'was removed from'
            }
        }
        return Embed(
            colour=e_dict[event]['clr'],
            title=guild.name,
            description=guild.description
        ).set_author(
            icon_url=guild.owner.avatar.url,
            name=f"The bot {e_dict[event]['word']} {str(guild.owner)}'s guild",
        ).set_thumbnail(
            url=guild.icon.url if guild.icon else None
        ).add_field(
            name='Members count',
            value=guild.member_count
        ).add_field(
            name='Guild ID',
            value=f'`{guild.id}`'
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        await self.bot.get_channel(Cid.global_logs).send(
            embed=self.guild_embed(guild, event='join')
        )
        query = 'INSERT INTO guilds (id, name) VALUES ($1, $2)'
        await self.bot.pool.execute(query, guild.id, guild.name)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        await self.bot.get_channel(Cid.global_logs).send(
            embed=self.guild_embed(guild, event='remove')
        )
        query = 'DELETE FROM guilds WHERE id=$1'
        await self.bot.pool.execute(query, guild.id)


class StatsCommands(commands.Cog, name='Stats'):
    """
    Some stats/infographics/diagrams/info

    More to come.
    """
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.help_emote = Ems.Smartge

    @commands.hybrid_command(
        name='wordcloud',
        description='Get `@member wordcloud over last total `limit` messages in requested `#channel`',
        usage='[channel(s)=curr] [member(s)=you] [limit=2000]'
    )
    @app_commands.describe(channel_or_and_member='List channel(-s) or/and member(-s)')
    async def wordcloud(
            self,
            ctx: Context,
            channel_or_and_member: commands.Greedy[Union[Member, TextChannel]] = None,
            limit: int = 2000
    ):
        """
        Get `@member`'s wordcloud over last total `limit` messages in requested `#channel`.
        Can accept multiple members/channels \
        Note that it's quite slow function or even infinitely slow with bigger limits ;
        """
        await ctx.typing()
        cm = channel_or_and_member or []  # idk i don't like mutable default argument warning
        members = [x for x in cm if isinstance(x, Member)] or [ctx.author]
        channels = [x for x in cm if isinstance(x, TextChannel)] or [ctx.channel]

        text = ''
        for ch in channels:
            text += ''.join([f'{msg.content}\n' async for msg in ch.history(limit=limit) if msg.author in members])
        # todo: remove this
        # wordcloud = WordCloud(width=640, height=360, max_font_size=40).generate(text)
        em = Embed(
            colour=Clr.prpl,
            description=(
                f"Members: {', '.join([m.mention for m in members])}\n"
                f"Channels: {', '.join([c.mention for c in channels])}\n"
                f"Limit: {limit}"
            )
        )
        # todo remove this
        #await ctx.reply(embed=em, file=img_to_file(wordcloud.to_image(), filename='wordcloud.png'))
        await ctx.reply('it does not work for now')


class StatsChannels(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.mytime.start()
        self.mymembers.start()
        self.mybots.start()

    def cog_unload(self) -> None:
        self.mytime.cancel()
        self.mymembers.cancel()
        self.mybots.cancel()

    @tasks.loop(time=[time(hour=x) for x in range(0, 24)])
    async def mytime(self):
        symbol = '#' if platform.system() == 'Windows' else '-'
        new_name = f'⏰ {datetime.now(timezone(timedelta(hours=3))).strftime(f"%{symbol}I %p")}, MSK, Aluerie time'
        await self.bot.get_channel(Cid.my_time).edit(name=new_name)

    @mytime.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=12)
    async def mymembers(self):
        guild = self.bot.get_guild(Sid.alu)
        bots_role = guild.get_role(Rid.bots)
        new_name = f'🏡 Members: {guild.member_count-len(bots_role.members)}'
        await guild.get_channel(795743012789551104).edit(name=new_name)

    @mymembers.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=5)
    async def mybots(self):
        guild = self.bot.get_guild(Sid.alu)
        bots_role = guild.get_role(Rid.bots)
        new_name = f'🤖 Bots: {len(bots_role.members)}'
        await guild.get_channel(795743065787990066).edit(name=new_name)

    @mybots.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Info(bot))
    await bot.add_cog(StatsChannels(bot))
    await bot.add_cog(StatsCommands(bot))
