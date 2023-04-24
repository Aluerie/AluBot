from __future__ import annotations

import colorsys
import datetime
import platform
import re
import socket
import warnings
from typing import TYPE_CHECKING, List, Union

import discord
import psutil
from dateparser.search import search_dates
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageColor

from utils.checks import is_owner
from utils.formats import format_dt_tdR, human_timedelta
from utils.var import MAP, MP, Cid, Clr, Ems, Rid, Sid

# from wordcloud import WordCloud

if TYPE_CHECKING:
    from utils.bot import AluBot
    from utils.context import Context

# Ignore dateparser warnings regarding pytz
warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)


async def account_age_ctx_menu(ntr: discord.Interaction, member: discord.Member):
    """View the age of an account."""
    age = datetime.datetime.now(datetime.timezone.utc) - member.created_at
    await ntr.response.send_message(f"{member.mention} is {human_timedelta(age)} old.", ephemeral=True)


class Info(commands.Cog, name='Info'):
    """Commands to get some useful info"""

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.ctx_menu2 = app_commands.ContextMenu(name='View Account Age', callback=account_age_ctx_menu)

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.PepoG)

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.ctx_menu2)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu2.name, type=self.ctx_menu2.type)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        pdates = search_dates(message.content)
        if pdates is None:
            return
        for pdate in pdates:
            dt = pdate[1]
            if dt.tzinfo is not None:
                e = discord.Embed(colour=Clr.prpl)
                e.description = (
                    f'"{pdate[0]}" in your timezone:\n {format_dt_tdR(dt)}\n'
                    f'{dt.tzname()} is GMT {dt.utcoffset().seconds / 3600:+.1f}, dls: {dt.dst().seconds / 3600:+.1f}'
                )
                await message.channel.send(embed=e)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.guild.id != Sid.alu:
            return
        added_role = list(set(after.roles) - set(before.roles))
        removed_role = list(set(before.roles) - set(after.roles))

        async def give_text_list(role_id, ch_id, msg_id):
            if (added_role and added_role[0].id == role_id) or (removed_role and removed_role[0].id == role_id):
                channel = before.guild.get_channel(ch_id)
                msg = channel.get_partial_message(msg_id)
                role = before.guild.get_role(role_id)
                e = discord.Embed(title=f'List of {role.name}', colour=Clr.prpl)
                e.description = ''.join([f'{member.mention}\n' for member in role.members])
                await msg.edit(content='', embed=e)

        await give_text_list(Rid.bots, Cid.bot_spam, 959982214827892737)
        await give_text_list(Rid.nsfw_bots, Cid.nsfw_bob_spam, 959982171492323388)

    @commands.hybrid_command(name='gmt', aliases=['utc'], description="Show GMT(UTC) time")
    async def gmt(self, ctx: Context):
        """Show GMT (UTC) time."""
        now_time = discord.utils.utcnow().strftime("%H:%M:%S")
        now_date = discord.utils.utcnow().strftime("%d/%m/%Y")
        e = discord.Embed(colour=Clr.prpl, title='GMT(Greenwich Mean Time)')
        e.set_footer(
            text=f'GMT is the same as UTC (Universal Time Coordinated)\nWith love, {ctx.guild.me.display_name}'
        )
        e.add_field(name='Time:', value=now_time)
        e.add_field(name='Date:', value=now_date)
        await ctx.reply(embed=e)

    @commands.hybrid_command(name='role', aliases=['members', 'roleinfo'], description="View info about selected role")
    @app_commands.describe(role='Choose role to get info about')
    async def roleinfo(self, ctx, *, role: discord.Role):
        """View info about selected role"""
        e = discord.Embed(title="Role information", colour=role.colour)
        e.description = '\n'.join([f'{counter} {m.mention}' for counter, m in enumerate(role.members, start=1)])
        await ctx.reply(embed=e)

    @commands.hybrid_command(
        aliases=['color'],
        usage='<formatted_colour_string>',
    )
    @app_commands.describe(colour='Colour in any of supported formats')
    async def colour(self, ctx, *, colour: str):
        """Get info about colour in specified <formatted_colour_string>

        The bot supports the following string formats:

        \N{BULLET} Hexadecimal specifiers: `#rgb`, `#rgba`, `#rrggbb` or `#rrggbbaa`
        \N{BULLET} RGB: `rgb(red, green, blue)` where the colour values are integers or percentages
        \N{BULLET} Hue-Saturation-Lightness (HSL): `hsl(hue, saturation%, lightness%)`
        \N{BULLET} Hue-Saturation-Value (HSV): `hsv(hue, saturation%, value%)`
        \N{BULLET} Common HTML color names: `red`, `Blue`
        \N{BULLET} Extra: MaterialUI Google Palette: `mu(colour_name, shade)`
        \N{BULLET} Extra: MateriaAccentUI Google Palette: `mu(colour_name, shade)`
        \N{BULLET} Last but not least: `prpl` for favourite Aluerie\'s colour
        """
        if colour == 'prpl':
            colour = '#9678B6'

        m = re.match(r"mu\(\s*([a-zA-Z]+)\s*,\s*(\d+)\s*\)$", colour)
        if m:
            colour = hex(MP.colors_dict[m.group(1)][int(m.group(2))]).replace('0x', '#')

        m = re.match(r"mua\(\s*([a-zA-Z]+)\s*,\s*(\d+)\s*\)$", colour)
        if m:
            colour = hex(MAP.colors_dict[m.group(1)][int(m.group(2))]).replace('0x', '#')

        rgb = ImageColor.getcolor(colour, "RGB")

        def rgb2hex(r, g, b):
            return "#{:02x}{:02x}{:02x}".format(r, g, b)

        img = Image.new('RGB', (300, 300), rgb)
        file = ctx.bot.imgtools.img_to_file(img, filename='colour.png')
        e = discord.Embed(color=discord.Colour.from_rgb(*rgb), title='Colour info')
        e.description = (
            f'Hex triplet: `{rgb2hex(*rgb)}`\n'
            + 'RGB: `({}, {}, {})`\n'.format(*rgb)
            + 'HSV: `({:.2f}, {:.2f}, {})`\n'.format(*colorsys.rgb_to_hsv(*rgb))
            + 'HLS: `({:.2f}, {}, {:.2f})`\n'.format(*colorsys.rgb_to_hls(*rgb))
        )
        e.set_thumbnail(url=f'attachment://{file.filename}')
        await ctx.reply(embed=e, file=file)

    @colour.autocomplete('colour')
    async def colour_callback(self, _: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        colours = ['prpl', 'rgb(', 'hsl(', 'hsv(', 'mu(', 'mua('] + list(ImageColor.colormap.keys())
        return [app_commands.Choice(name=clr, value=clr) for clr in colours if current.lower() in clr.lower()][:25]

    @colour.error
    async def colour_error(self, ctx, error):
        if isinstance(
            error, (commands.HybridCommandError, commands.CommandInvokeError, app_commands.CommandInvokeError)
        ):
            error = error.original
            if isinstance(error, (commands.CommandInvokeError, app_commands.CommandInvokeError)):
                error = error.original

        if isinstance(error, (ValueError, KeyError)):
            # todo: new error type implement
            ctx.error_handled = True
            e = discord.Embed(description=self.colour.callback.__doc__, colour=Clr.error)
            e.set_author(
                name='WrongColourFormat', url='https://pillow.readthedocs.io/en/stable/reference/ImageColor.html'
            )
            await ctx.reply(embed=e, ephemeral=True)

    @is_owner()
    @commands.command(
        name='sysinfo',
        description='Get system info about machine currently hosting the bot',
        aliases=['systeminfo'],
        hidden=True,
    )
    async def sysinfo(self, ctx: Context):
        """Get system info about machine currently hosting the bot"""
        url = 'https://ipinfo.io/json'
        async with self.bot.session.get(url) as resp:
            data = await resp.json()

        e = discord.Embed(title="Bot Host Machine System Info", colour=Clr.prpl)
        e.description = (
            f'\N{BLACK CIRCLE} Hostname: {socket.gethostname()}\n'
            f'\N{BLACK CIRCLE} Machine: {platform.machine()}\n'
            f'\N{BLACK CIRCLE} Platform: {platform.platform()}\n'
            f'\N{BLACK CIRCLE} System: `{platform.system()}` release: `{platform.release()}`\n'
            f'\N{BLACK CIRCLE} Version: `{platform.version()}`\n'
            f'\N{BLACK CIRCLE} Processor: {platform.processor()}\n'
        )
        e.add_field(
            name='Current % | max values',
            value=(
                # f'\N{BLACK CIRCLE} CPU usage: \n{psutil.cpu_percent()}% | {psutil.cpu_freq().current / 1000:.1f}GHz\n'
                f'\N{BLACK CIRCLE} RAM usage: \n{psutil.virtual_memory().percent}% | '
                f'{str(round(psutil.virtual_memory().total / (1024.0 ** 3))) + " GB"}\n'
                f'\N{BLACK CIRCLE} Disk usage: \n{(du := psutil.disk_usage("/")).percent} % | '
                f'{du.used / (1024 ** 3):.1f}GB/{du.total / (1024 ** 3):.1f}GB'
            ),
        )
        e.set_footer(text=f'AluBot is a copyright 2020-{discord.utils.utcnow().year} of {self.bot.owner.name}')
        if not self.bot.test:
            e.add_field(
                name="Bot\'s Location judging by IP", value=f"· {data['country']} {data['region']} {data['city']}"
            )
        await ctx.reply(embed=e)


class StatsCommands(commands.Cog, name='Stats'):
    """Some stats/infographics/diagrams/info

    More to come.
    """

    def __init__(self, bot):
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.Smartge)

    @commands.hybrid_command(
        name='wordcloud',
        description='Get `@member wordcloud over last total `limit` messages in requested `#channel`',
        usage='[channel(s)=curr] [member(s)=you] [limit=2000]',
    )
    @app_commands.describe(channel_or_and_member='List channel(-s) or/and member(-s)')
    async def wordcloud(
        self,
        ctx: Context,
        channel_or_and_member: commands.Greedy[Union[discord.Member, discord.TextChannel]] = None,
        limit: int = 2000,
    ):
        """Get `@member`'s wordcloud over last total `limit` messages in requested `#channel`.

        Can accept multiple members/channels \
        Note that it's quite slow function or even infinitely slow with bigger limits ;
        """
        await ctx.typing()
        cm = channel_or_and_member or []  # idk i don't like mutable default argument warning
        members = [x for x in cm if isinstance(x, discord.Member)] or [ctx.author]
        channels = [x for x in cm if isinstance(x, discord.TextChannel)] or [ctx.channel]

        text = ''
        for ch in channels:
            text += ''.join([f'{msg.content}\n' async for msg in ch.history(limit=limit) if msg.author in members])
        # wordcloud = WordCloud(width=640, height=360, max_font_size=40).generate(text)
        e = discord.Embed(colour=Clr.prpl)
        e.description = (
            f"Members: {', '.join([m.mention for m in members])}\n"
            f"Channels: {', '.join([c.mention for c in channels])}\n"
            f"Limit: {limit}"
        )
        # await ctx.reply(embed=e, file=img_to_file(wordcloud.to_image(), filename='wordcloud.png'))
        await ctx.reply('it does not work for now, waiting those guys to fix it')


async def setup(bot: AluBot):
    await bot.add_cog(Info(bot))
    await bot.add_cog(StatsCommands(bot))
