from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Literal, Optional

import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps

from utils import const
from utils.dota import ability, hero, item
from utils.dota.const import dota_player_colour_map
from utils.formats import human_timedelta

if TYPE_CHECKING:
    from bot import AluBot
    from utils.twitch import TwitchClient


__all__ = (
    "Match",
    "ActiveMatch",
    "PostMatchPlayerData",
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Match:
    def __init__(self, match_id: int):
        self.match_id = match_id

    @property
    def dbuff(self) -> str:
        """Dotabuff.com link for the match with `match_id`"""
        return f"https://www.dotabuff.com/matches/{self.match_id}"

    @property
    def odota(self) -> str:
        """Opendota.com link for the match with `match_id`"""
        return f"https://www.opendota.com/matches/{self.match_id}"

    @property
    def stratz(self) -> str:
        """Stratz.com link for `match_id`"""
        return f"https://www.stratz.com/matches/{self.match_id}"

    def replay(self, matchtime: int = 0) -> str:
        """replay link which opens dota 2 client"""
        return f"dota2://matchid={self.match_id}&matchtime={matchtime}"

    @property
    def links(self) -> str:
        """all links at once"""
        return f"/[Dbuff]({self.dbuff})/[ODota]({self.odota})/[Stratz]({self.stratz})"


colour_twitch_status_dict = {
    "NoTwitch": const.MaterialPalette.gray(),
    "Live": const.Colour.prpl(),
    "Offline": const.Colour.twitch(),
}


class ActiveMatch(Match):
    img_url: str
    display_name: str
    url: str
    logo_url: str
    vod_link: str
    colour: discord.Colour
    twitch_status: str

    hero_name: str

    def __init__(
        self,
        *,
        match_id: int,
        start_time: int,
        player_name: str,
        hero_id: int,
        hero_ids: list[int],
        server_steam_id: int,
        twitchtv_id: Optional[int] = None,
        channel_ids: list[int],
    ):
        super().__init__(match_id)
        self.start_time = start_time
        self.player_name = player_name
        self.hero_id = hero_id
        self.hero_ids = hero_ids
        self.server_steam_id = server_steam_id
        self.twitchtv_id = twitchtv_id
        self.channel_ids = channel_ids

    @property
    def long_ago(self) -> int:
        return int(discord.utils.utcnow().timestamp()) - self.start_time

    async def get_twitch_data(self, twitch: TwitchClient):
        if self.twitchtv_id is None:
            self.img_url = "https://i.imgur.com/kl0jDOu.png"  # lavender 640x360
            self.display_name = self.player_name
            self.url = ""
            self.logo_url = const.Logo.dota
            self.twitch_status = "NoTwitch"
            self.vod_link = ""
        else:
            ts = await twitch.get_twitch_stream(self.twitchtv_id)
            self.img_url = ts.preview_url
            self.display_name = ts.display_name
            self.logo_url = ts.logo_url
            self.url = ts.url
            if ts.online:
                self.twitch_status = "Live"
                self.vod_link = await twitch.last_vod_link(self.twitchtv_id, seconds_ago=self.long_ago)
            else:
                self.twitch_status = "Offline"
                self.vod_link = ""
        self.colour = colour_twitch_status_dict[self.twitch_status]

    async def better_thumbnail(self, bot: AluBot) -> Image.Image:
        img = await bot.transposer.url_to_image(self.img_url)
        width, _height = img.size
        rectangle = Image.new("RGB", (width, 70), str(self.colour))
        ImageDraw.Draw(rectangle)
        img.paste(rectangle)

        for count, hero_id in enumerate(self.hero_ids):
            hero_img = await bot.transposer.url_to_image(await hero.img_url_by_id(hero_id))
            # h_width, h_height = heroImg.size
            hero_img = hero_img.resize((62, 35))
            hero_img = ImageOps.expand(hero_img, border=(0, 3, 0, 0), fill=dota_player_colour_map.get(count, "#FF0000"))
            extra_space = 0 if count < 5 else 20
            img.paste(hero_img, (count * 62 + extra_space, 0))

        font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)
        draw = ImageDraw.Draw(img)
        text = f"{self.display_name} - {self.hero_name}"
        w2, h2 = bot.transposer.get_text_wh(text, font)
        draw.text(((width - w2) / 2, 35), text, font=font, align="center")

        w2, h2 = bot.transposer.get_text_wh(text, font)
        draw.text((0, 35 + h2 + 10), self.twitch_status, font=font, align="center", fill=str(self.colour))
        return img

    async def notif_embed_and_file(self, bot: AluBot) -> tuple[discord.Embed, discord.File]:
        log.debug("Creating embed+file for notification")

        # settings hero_name since ours is async and cant be done in init
        self.hero_name = await hero.name_by_id(self.hero_id)

        await self.get_twitch_data(bot.twitch)
        img_file = bot.transposer.image_to_file(
            await self.better_thumbnail(bot),
            filename=(
                f'{self.twitch_status}-{self.display_name.replace("_", "")}-'
                f'{(self.hero_name).replace(" ", "").replace(chr(39), "")}.png'  # chr39 is "'"
            ),
        )
        e = discord.Embed(colour=self.colour, url=self.url)
        e.description = (
            f"`/match {self.match_id}` started {human_timedelta(self.long_ago, strip=True)}\n"
            f"{self.vod_link}{self.links}"
        )
        e.set_image(url=f"attachment://{img_file.filename}")
        e.set_thumbnail(url=await hero.img_url_by_id(self.hero_id))
        e.set_author(name=f"{self.display_name} - {self.hero_name}", url=self.url, icon_url=self.logo_url)
        e.set_footer(text=f"watch_server {self.server_steam_id}")
        return e, img_file


class PostMatchPlayerData:
    """
    Class
    """

    def __init__(
        self,
        *,
        player_data: dict,
        channel_id: int,
        message_id: int,
        twitch_status: Literal["NoTwitch", "Offline", "Online"],
        api_calls_done: int,
    ):
        self.channel_id = channel_id
        self.message_id = message_id
        self.twitch_status = twitch_status
        self.api_calls_done = api_calls_done

        self.colour = colour_twitch_status_dict[self.twitch_status]

        self.match_id: int = player_data["match_id"]
        self.hero_id: int = player_data["hero_id"]
        self.outcome = "Win" if player_data["win"] else "Loss"
        self.ability_upgrades_arr = player_data["ability_upgrades_arr"]
        self.items = [player_data[f"item_{i}"] for i in range(6)]
        self.kda = f'{player_data["kills"]}/{player_data["deaths"]}/{player_data["assists"]}'
        self.purchase_log = player_data["purchase_log"]
        self.aghs_blessing = False
        self.aghs_shard = False
        permanent_buffs = player_data["permanent_buffs"] or []  # [] if it is None
        for pb in permanent_buffs:
            if pb["permanent_buff"] == 12:
                self.aghs_shard = True
            if pb["permanent_buff"] == 2:
                self.aghs_blessing = True

    def __repr__(self) -> str:
        pairs = " ".join([f"{k}={v!r}" for k, v in self.__dict__.items()])
        return f"<{self.__class__.__name__} {pairs}>"

    async def edit_the_image(self, img_url, bot: AluBot):
        img = await bot.transposer.url_to_image(img_url)

        width, height = img.size
        last_row_h = 50

        rectangle = Image.new("RGB", (width, last_row_h), str(self.colour))
        ImageDraw.Draw(rectangle)

        last_row_y = height - last_row_h
        img.paste(rectangle, (0, last_row_y))

        font_kda = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 26)

        draw = ImageDraw.Draw(img)
        w3, h3 = bot.transposer.get_text_wh(self.kda, font_kda)
        draw.text((0, height - h3), self.kda, font=font_kda, align="right")

        draw = ImageDraw.Draw(img)
        w2, h2 = bot.transposer.get_text_wh(self.outcome, font_kda)
        colour_dict = {
            "Win": str(const.MaterialPalette.green(shade=800)),
            "Loss": str(const.MaterialPalette.red(shade=900)),
            "Not Scored": (255, 255, 255),
        }
        draw.text((0, height - h3 - h2), self.outcome, font=font_kda, align="center", fill=colour_dict[self.outcome])

        font_m = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 19)

        async def item_timing_text(item_id, x_left):
            for i in reversed(self.purchase_log):
                if item_id == await item.id_by_key(i["key"]):
                    text = f"{math.ceil(i['time']/60)}m"
                    w7, h7 = bot.transposer.get_text_wh(text, font_m)
                    draw.text((x_left, height - h7), text, font=font_m, align="left")
                    return

        left_i = width - 69 * 6
        for count, itemId in enumerate(self.items):
            hero_img = await bot.transposer.url_to_image(await item.iconurl_by_id(itemId))
            # h_width, h_height = heroImg.size # naturally in (88, 64)
            hero_img = hero_img.resize((69, 50))  # 69/50 - to match 88/64
            curr_left = left_i + count * hero_img.width
            img.paste(hero_img, (curr_left, height - hero_img.height))
            await item_timing_text(itemId, curr_left)

        ability_h = 37
        for count, abilityId in enumerate(self.ability_upgrades_arr):
            abil_img = await bot.transposer.url_to_image(await ability.iconurl_by_id(abilityId))
            abil_img = abil_img.resize((ability_h, ability_h))
            img.paste(abil_img, (count * ability_h, last_row_y - abil_img.height))

        talent_strs = []
        for x in self.ability_upgrades_arr:
            if (dname := await ability.name_by_id(x)) is not None:
                talent_strs.append(dname)

        font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 12)
        for count, txt in enumerate(talent_strs):
            draw = ImageDraw.Draw(img)
            w4, h4 = bot.transposer.get_text_wh(txt, font)
            draw.text((width - w4, last_row_y - 30 * 2 - 22 * count), txt, font=font, align="right")
        right = left_i
        if self.aghs_blessing:
            bless_img = await bot.transposer.url_to_image(ability.lazy_aghs_bless_url)
            bless_img = bless_img.resize((48, 35))
            img.paste(bless_img, (right - bless_img.width, height - bless_img.height))
            await item_timing_text(271, right - bless_img.width)
            right -= bless_img.width
        if self.aghs_shard:
            shard_img = await bot.transposer.url_to_image(ability.lazy_aghs_shard_url)
            shard_img = shard_img.resize((48, 35))
            img.paste(shard_img, (right - shard_img.width, height - shard_img.height))
            await item_timing_text(609, right - shard_img.width)

        # img.show()
        return img

    async def edit_the_embed(self, bot: AluBot):
        ch = bot.get_channel(self.channel_id)
        if ch is None:
            return  # wrong bot, I guess

        try:
            assert isinstance(ch, discord.TextChannel)
            msg = await ch.fetch_message(self.message_id)
        except discord.NotFound:
            return

        e = msg.embeds[0]
        img_file = bot.transposer.image_to_file(await self.edit_the_image(e.image.url, bot), filename="edited.png")
        e.set_image(url=f"attachment://{img_file.filename}")
        if self.channel_id == const.Channel.repost:
            e.set_footer(text=f'{e.footer.text or ""} | {self.api_calls_done}')
        try:
            await msg.edit(embed=e, attachments=[img_file])
        except discord.Forbidden:
            return
