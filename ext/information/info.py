from __future__ import annotations

import colorsys
import warnings
from typing import TYPE_CHECKING

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

# Ignore dateparser warnings regarding pytz
warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)


class Info(InfoCog, name="Info", emote=const.Emote.PepoG):
    """Commands to get some useful info."""

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        parsed_dates = search_dates(message.content)
        if not parsed_dates:
            return
        for date in parsed_dates:
            dt = date[1]
            if dt.tzinfo is not None:
                e = discord.Embed(colour=const.Colour.prpl)
                utc_offset = o.seconds if (o := dt.utcoffset()) else 0
                dst = d.seconds if (d := dt.dst()) else 0
                e.description = (
                    f'"{date[0]}" in your timezone:\n {formats.format_dt_tdR(dt)}\n'
                    f"{dt.tzname()} is GMT {utc_offset / 3600:+.1f}, dst: {dst / 3600:+.1f}"
                )
                await message.channel.send(embed=e)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.guild.id != const.Guild.community:
            return
        added_role = list(set(after.roles) - set(before.roles))
        removed_role = list(set(before.roles) - set(after.roles))

        async def give_text_list(role: discord.Role, channel: discord.TextChannel, msg_id: int) -> None:
            if (added_role and added_role[0] == role) or (removed_role and removed_role[0] == role):
                msg = channel.get_partial_message(msg_id)
                e = discord.Embed(title=f"List of {role.name}", colour=const.Colour.prpl)
                e.description = "".join([f"{member.mention}\n" for member in role.members])
                await msg.edit(content="", embed=e)

        await give_text_list(self.community.bots_role, self.community.bot_spam, 959982214827892737)
        await give_text_list(self.community.nsfw_bots_role, self.community.nsfw_bot_spam, 959982171492323388)

    @app_commands.command(name="gmt")
    async def gmt(self, interaction: discord.Interaction[AluBot]) -> None:
        """Show GMT (UTC) time."""
        now_time = discord.utils.utcnow().strftime("%H:%M:%S")
        now_date = discord.utils.utcnow().strftime("%d/%m/%Y")
        embed = (
            discord.Embed(
                colour=const.Colour.prpl,
                title="GMT (Greenwich Mean Time)",
            )
            .set_footer(text="GMT is the same as UTC (Universal Time Coordinated)")
            .add_field(name="Time:", value=now_time)
            .add_field(name="Date:", value=now_date)
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="role")
    @app_commands.describe(role="Choose role to get info about")
    async def role_info(self, interaction: discord.Interaction[AluBot], role: discord.Role) -> None:
        """View info about selected role."""
        embed = discord.Embed(
            colour=role.colour,
            title="Role information",
            description=f"Role {role.mention}\n"
            + "\n".join(
                [f"{counter} {m.mention}" for counter, m in enumerate(role.members, start=1)],
            ),
        )

        await interaction.response.send_message(embed=embed)
        # todo: make pagination about it^.
        # Also add stuff like colour code, amount of members and some garbage other bots include

    @app_commands.command()
    @app_commands.describe(colour="Colour in any of supported formats")
    async def colour(
        self,
        interaction: discord.Interaction[AluBot],
        colour: app_commands.Transform[discord.Colour, converters.AluColourTransformer],
    ) -> None:
        r"""Get info about colour in specified <formatted_colour_string>.

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
        file = interaction.client.transposer.image_to_file(img, filename="colour.png")
        e = discord.Embed(color=discord.Colour.from_rgb(*rgb), title="Colour info")
        e.description = (
            "Hex triplet: `#{:02x}{:02x}{:02x}`\n".format(*rgb)
            + "RGB: `({}, {}, {})`\n".format(*rgb)
            + "HSV: `({:.2f}, {:.2f}, {})`\n".format(*colorsys.rgb_to_hsv(*rgb))
            + "HLS: `({:.2f}, {}, {:.2f})`\n".format(*colorsys.rgb_to_hls(*rgb))
        )
        e.set_thumbnail(url=f"attachment://{file.filename}")
        await interaction.response.send_message(embed=e, file=file)

    @colour.autocomplete("colour")
    async def autocomplete(self, _: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        colours = ["prpl", "rgb(", "hsl(", "hsv(", "mp(", "map(", *list(ImageColor.colormap.keys())]
        return [
            app_commands.Choice(name=Colour, value=Colour) for Colour in colours if current.lower() in Colour.lower()
        ][:25]


class StatsCommands(InfoCog, name="Stats Commands", emote=const.Emote.Smartge):
    """Some stats/infographics/diagrams/info.

    More to come.
    """

    @app_commands.guild_only()
    @app_commands.command(name="wordcloud")
    @app_commands.rename(member_="member", channel_="channel")
    async def wordcloud(
        self,
        interaction: discord.Interaction[AluBot],
        member_: discord.Member | None = None,
        channel_: discord.TextChannel | None = None,
        limit: app_commands.Range[int, 2000] = 1000,
    ) -> None:
        """Get `@member`'s wordcloud over last total `limit` messages in requested `#channel`.

        I do not scrap any chat histories into my own database.
        This is why this command is limited and slow because the bot has to look up channel histories in place.

        Parameters
        ----------
        """
        await interaction.response.defer()

        member = member_ or interaction.user
        channel = channel_ or interaction.channel
        assert (
            channel
            and not isinstance(channel, discord.ForumChannel)
            and not isinstance(channel, discord.CategoryChannel)
        )

        text = "".join([f"{msg.content}\n" async for msg in channel.history(limit=limit) if msg.author == member])
        wordcloud = WordCloud(width=640, height=360, max_font_size=40).generate(text)
        embed = discord.Embed(
            colour=const.Colour.prpl,
            description=f"Member: {member}\nChannel: {channel}\nLimit: {limit}",
        )
        file = self.bot.transposer.image_to_file(wordcloud.to_image(), filename="wordcloud.png")
        await interaction.followup.send(embed=embed, file=file)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Info(bot))
    await bot.add_cog(StatsCommands(bot))
