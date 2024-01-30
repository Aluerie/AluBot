from __future__ import annotations

import colorsys
import warnings
from typing import TYPE_CHECKING, Annotated, Union

import discord
from dateparser.search import search_dates
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageColor
from wordcloud import WordCloud

from utils import const, converters, formats

from ._base import InfoCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext

# Ignore dateparser warnings regarding pytz
warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)


class Info(InfoCog, name="Info", emote=const.Emote.PepoG):
    """Commands to get some useful info"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx_menu_avatar = app_commands.ContextMenu(
            name="View User Avatar",
            callback=self.view_user_avatar,
        )

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.ctx_menu_avatar)

    async def cog_unload(self) -> None:
        c = self.ctx_menu_avatar
        self.bot.tree.remove_command(c.name, type=c.type)

    async def view_user_avatar(self, interaction: discord.Interaction, user: discord.User):
        embed = discord.Embed(color=user.colour, title=f"Avatar for {user.display_name}").set_image(
            url=user.display_avatar.url
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
                e = discord.Embed(colour=const.Colour.blueviolet)
                utc_offset = o.seconds if (o := dt.utcoffset()) else 0
                dst = d.seconds if (d := dt.dst()) else 0
                e.description = (
                    f'"{pdate[0]}" in your timezone:\n {formats.format_dt_tdR(dt)}\n'
                    f"{dt.tzname()} is GMT {utc_offset / 3600:+.1f}, dst: { dst / 3600:+.1f}"
                )
                await message.channel.send(embed=e)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.guild.id != const.Guild.community:
            return
        added_role = list(set(after.roles) - set(before.roles))
        removed_role = list(set(before.roles) - set(after.roles))

        async def give_text_list(role: discord.Role, channel: discord.TextChannel, msg_id):
            if (added_role and added_role[0] == role) or (removed_role and removed_role[0] == role):
                msg = channel.get_partial_message(msg_id)
                e = discord.Embed(title=f"List of {role.name}", colour=const.Colour.blueviolet)
                e.description = "".join([f"{member.mention}\n" for member in role.members])
                await msg.edit(content="", embed=e)

        await give_text_list(self.community.bots_role, self.community.bot_spam, 959982214827892737)
        await give_text_list(self.community.nsfw_bots_role, self.community.nsfw_bot_spam, 959982171492323388)

    @commands.hybrid_command(name="gmt", aliases=["utc"], description="Show GMT(UTC) time")
    async def gmt(self, ctx: AluContext):
        """Show GMT (UTC) time."""
        now_time = discord.utils.utcnow().strftime("%H:%M:%S")
        now_date = discord.utils.utcnow().strftime("%d/%m/%Y")
        e = discord.Embed(colour=const.Colour.blueviolet, title="GMT(Greenwich Mean Time)")
        e.set_footer(text=f"GMT is the same as UTC (Universal Time Coordinated)")
        e.add_field(name="Time:", value=now_time).add_field(name="Date:", value=now_date)
        await ctx.reply(embed=e)

    @commands.hybrid_command(name="role")
    @app_commands.describe(role="Choose role to get info about")
    async def role_info(self, ctx: AluContext, *, role: discord.Role):
        """View info about selected role."""
        e = discord.Embed(title="Role information", colour=role.colour)
        msg = f"Role {role.mention}\n"
        msg += "\n".join([f"{counter} {m.mention}" for counter, m in enumerate(role.members, start=1)])
        e.description = msg
        await ctx.reply(embed=e)
        # todo: make pagination about it^.
        # Also add stuff like colour code, amount of members and some garbage other bots include

    @commands.hybrid_command(
        aliases=["color"],
        usage="<formatted_colour_string>",
    )
    @app_commands.describe(colour="Colour in any of supported formats")
    async def colour(self, ctx, *, colour: Annotated[discord.Colour, converters.AluColourConverter]):
        """Get info about colour in specified <formatted_colour_string>

        The bot supports the following string formats:

        \N{BULLET} Hexadecimal specifiers: `#rgb`, `#rgba`, `#rrggbb` or `#rrggbbaa`, `0x<hex>`, `#<hex>`, `0x#<hex>`
        \N{BULLET} RGB: `rgb(red, green, blue)` where the colour values are integers or percentages
        \N{BULLET} Hue-Saturation-Lightness (HSL): `hsl(hue, saturation%, lightness%)`
        \N{BULLET} Hue-Saturation-Value (HSV): `hsv(hue, saturation%, value%)`
        \N{BULLET} Common HTML or discord color names: `red`, `Blue`
        \N{BULLET} Extra: MaterialUI Google Palette: `mp(colour_name, shade)`
        \N{BULLET} Extra: MateriaAccentUI Google Palette: `map(colour_name, shade)`
        \N{BULLET} Last but not least: `prpl` for favourite Aluerie\'s colour
        """
        rgb = colour.to_rgb()

        img = Image.new("RGB", (300, 300), rgb)
        file = ctx.bot.imgtools.img_to_file(img, filename="colour.png")
        e = discord.Embed(color=discord.Colour.from_rgb(*rgb), title="Colour info")
        e.description = (
            "Hex triplet: `#{:02x}{:02x}{:02x}`\n".format(*rgb)
            + "RGB: `({}, {}, {})`\n".format(*rgb)
            + "HSV: `({:.2f}, {:.2f}, {})`\n".format(*colorsys.rgb_to_hsv(*rgb))
            + "HLS: `({:.2f}, {}, {:.2f})`\n".format(*colorsys.rgb_to_hls(*rgb))
        )
        e.set_thumbnail(url=f"attachment://{file.filename}")
        await ctx.reply(embed=e, file=file)

    @colour.autocomplete("colour")
    async def autocomplete(self, _: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        colours = ["prpl", "rgb(", "hsl(", "hsv(", "mp(", "map("] + list(ImageColor.colormap.keys())
        return [
            app_commands.Choice(name=Colour, value=Colour) for Colour in colours if current.lower() in Colour.lower()
        ][:25]


class StatsCommands(InfoCog, name="Stats", emote=const.Emote.Smartge):
    """Some stats/infographics/diagrams/info

    More to come.
    """

    @commands.hybrid_command(name="wordcloud", usage="[channel(s)=curr] [member(s)=you] [limit=2000]")
    @app_commands.describe(channel_or_and_member="List channel(-s) or/and member(-s)")
    async def wordcloud(
        self,
        ctx: AluContext,
        channel_or_and_member: commands.Greedy[Union[discord.Member, discord.TextChannel]],
        limit: commands.Range[int, 2000],
    ):
        """Get `@member`'s wordcloud over last total `limit` messages in requested `#channel`.

        I do not scrap any chat histories into my own database.
        This is why this command is limited and slow because the bot has to look up channel histories in place.
        """
        await ctx.typing()
        cm = channel_or_and_member or []  # idk i don't like mutable default argument warning
        members = [x for x in cm if isinstance(x, discord.Member)] or [ctx.author]
        channels = [x for x in cm if isinstance(x, discord.TextChannel)] or [ctx.channel]

        text = ""
        for ch in channels:
            text += "".join([f"{msg.content}\n" async for msg in ch.history(limit=limit) if msg.author in members])
        wordcloud = WordCloud(width=640, height=360, max_font_size=40).generate(text)
        e = discord.Embed(colour=const.Colour.blueviolet)
        members = ", ".join([m.mention for m in members])
        channels = ", ".join(
            [c.mention if isinstance(c, discord.TextChannel) else c.__class__.__name__ for c in channels]
        )

        e.description = f"Members: {members}\nChannels: {channels}\nLimit: {limit}"
        file = self.bot.transposer.image_to_file(wordcloud.to_image(), filename="wordcloud.png")
        await ctx.reply(embed=e, file=file)


async def setup(bot: AluBot):
    await bot.add_cog(Info(bot))
    await bot.add_cog(StatsCommands(bot))
