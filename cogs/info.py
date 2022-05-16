from discord import Interaction, Embed, Member, Message, Role, Colour, app_commands
from discord.ext import commands, tasks

from utils.format import humanize_time
from utils.var import *
from utils.imgtools import img_to_file

from datetime import datetime, timezone
from PIL import Image, ImageColor
import colorsys
from async_google_trans_new import google_translator


async def account_age_ctx_menu(ntr: Interaction, member: Member):
    """View the age of an account."""
    age = datetime.now(timezone.utc) - member.created_at
    await ntr.response.send_message(f"{member.mention} is {humanize_time(age)} old.", ephemeral=True)


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reload_info.start()
        self.help_category = 'Info'

        self.ctx_menu = app_commands.ContextMenu(name='View Account Age', callback=account_age_ctx_menu)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.guild.id != Sid.irene:
            return
        irene_server = self.bot.get_guild(Sid.irene)
        added_role = list(set(after.roles) - set(before.roles))
        removed_role = list(set(before.roles) - set(after.roles))

        async def give_text_list(role_id, ch_id, msg_id):
            if (added_role and added_role[0].id == role_id) or (removed_role and removed_role[0].id == role_id):
                channel = irene_server.get_channel(ch_id)
                msg = channel.get_partial_message(msg_id)
                role = irene_server.get_role(role_id)
                embed = Embed(colour=Clr.prpl, title=f'List of {role.name}')
                embed.description = ''.join([f'{member.mention}\n' for member in role.members])
                await msg.edit(content='', embed=embed)
        await give_text_list(Rid.bots, Cid.bot_spam, 959982214827892737)
        await give_text_list(Rid.nsfwbots, Cid.nsfw_bob_spam, 959982171492323388)

    @commands.hybrid_command(
        name='gmt',
        brief=Ems.slash,
        aliases=['utc'],
        description="Show GMT(UTC) time"
    )
    async def gmt(self, ctx):
        """Show GMT(UTC) time ;"""
        now_time = datetime.now(timezone.utc).strftime("%H:%M:%S")
        now_date = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        embed = Embed(colour=Clr.prpl, title='GMT(Greenwich Mean Time)')
        embed.set_footer(
            text=f'GMT is the same as UTC (Universal Time Coordinated)\nWith love, {ctx.guild.me.display_name}')
        embed.add_field(name='Time:', value=now_time)
        embed.add_field(name='Date:', value=now_date)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(
        brief=Ems.slash,
        name='role',
        aliases=['members', 'roleinfo'],
        description="View info about selected role"
    )
    async def roleinfo(self, ctx, *, role: Role):
        """View info about selected role"""
        embed = Embed(colour=role.colour, title="Role information")  # TODO: this embed will be more than 6000 symbols
        embed.description = '\n'.join([f'{counter} {m.mention}' for counter, m in enumerate(role.members, start=1)])
        await ctx.reply(embed=embed)

    @tasks.loop(count=1)
    async def reload_info(self):
        embed = Embed(colour=Clr.prpl, description=f'Logged in as {self.bot.user}')
        for i in [Cid.spam_me, Cid.logs]:
            await self.bot.get_channel(i).send(embed=embed)

    @reload_info.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def translate_msg_ctx_menu(ntr: Interaction, message: Message):
    embed = Embed(colour=message.author.colour, title='Google Translate to English')
    if len(message.content) == 0:
        embed.description = "Sorry it seems this message doesn't have content"
    else:
        translator = google_translator()
        embed.description = await translator.translate(message.content, lang_tgt='en')
        embed.set_footer(text=f'Detected language: {(await translator.detect(message.content))[0]}')
    await ntr.response.send_message(embed=embed, ephemeral=True)


class InfoTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Tools'
        self.ctx_menu = app_commands.ContextMenu(name='Translate to English', callback=translate_msg_ctx_menu)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.hybrid_command(
        name='translate',
        description='Translate text to English, auto-detects source language',
        brief=Ems.slash
    )
    @app_commands.describe(text="Enter text to translate")
    async def translate(self, ctx, *, text: str):
        """Translate text into English using Google Translate, auto-detects source language"""
        translator = google_translator()
        embed = Embed(colour=ctx.author.colour, title='Google Translate to English')
        embed.description = await translator.translate(text, lang_tgt='en')
        embed.set_footer(text=f'Detected language: {(await translator.detect(text))[0]}')
        await ctx.reply(embed=embed)

    @commands.hybrid_command(
        name='colour',
        brief=Ems.slash,
        description="Get info about colour",
        aliases=['color'],
        usage='<formatted colour string>'
    )
    @app_commands.describe(string='Colour in any of supported formats')
    async def colour(self, ctx, *, string: str):
        if string == 'prpl':
            string = '#9678B6'
        rgb = ImageColor.getcolor(string, "RGB")

        def rgb2hex(r, g, b):
            return "#{:02x}{:02x}{:02x}".format(r, g, b)

        embed = Embed(color=Colour.from_rgb(*rgb), title='Colour info')
        embed.description = \
            f'Hex triplet: `{rgb2hex(*rgb)}`\n' + \
            'RGB: `({}, {}, {})`\n'.format(*rgb) + \
            'HSV: `({:.2f}, {:.2f}, {})`\n'.format(*colorsys.rgb_to_hsv(*rgb)) + \
            'HLS: `({:.2f}, {}, {:.2f})`\n'.format(*colorsys.rgb_to_hls(*rgb))

        img = Image.new('RGB', (300, 300), rgb)
        file = img_to_file(img, filename='colour.png')
        embed.set_thumbnail(url=f'attachment://{file.filename}')
        await ctx.reply(embed=embed, file=file)

    @colour.error
    async def colour_error(self, ctx, error):
        if isinstance(error, ValueError):
            ctx.error_handled = True
            embed = Embed(colour=Clr.error)
            embed.set_author(name='WrongColourFormat')
            embed.url = 'https://pillow.readthedocs.io/en/stable/reference/ImageColor.html'
            embed.title = 'Wrong colour format'
            embed.description = \
                'The bot supports the following string formats:\n' \
                '● Hexadecimal specifiers: `#rgb`, `#rgba`, `#rrggbb` or `#rrggbbaa`\n' \
                '● RGB: `rgb(red, green, blue)` where the colour values are integers or percentages\n' \
                '● Hue-Saturation-Lightness (HSL): `hsl(hue, saturation%, lightness%)`\n' \
                '● Hue-Saturation-Value (HSV): `hsv(hue, saturation%, value%)`\n' \
                '● Common HTML color names: `red`, `Blue`' \
                '● Also `prpl` for favourite Irene\'s colour '
            await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(Info(bot))
    await bot.add_cog(InfoTools(bot))
