from __future__ import annotations

import asyncio
import datetime
import logging
import math
from typing import TYPE_CHECKING, Literal, Optional, TypedDict, override

import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps

from utils import const, dota, formats

from .._fpc_utils.base_models import BasePostMatchPlayer

if TYPE_CHECKING:
    from bot import AluBot
    from utils.twitch import TwitchClient


__all__ = (
    "Match",
    "ActiveMatch",
    "PostMatchPlayerData",
)
type LiteralTwitchStatus = Literal["NoTwitch", "Offline", "Live"]


class TwitchData(TypedDict):
    preview_url: str
    display_name: str
    url: str
    logo_url: str
    vod_url: str
    twitch_status: LiteralTwitchStatus
    colour: discord.Colour


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


class ActiveMatch(Match):
    def __init__(
        self,
        *,
        match_id: int,
        start_time: int,
        player_name: str,
        hero_id: int,
        hero_ids: list[int],
        server_steam_id: int,
        twitch_id: Optional[int] = None,
        channel_ids: list[int],
        hero_name: str,
    ):
        super().__init__(match_id)
        self.start_time: int = start_time
        self.player_name: str = player_name
        self.hero_id: int = hero_id
        self.hero_ids: list[int] = hero_ids
        self.server_steam_id: int = server_steam_id
        self.twitch_id: Optional[int] = twitch_id
        self.channel_ids: list[int] = channel_ids
        self.hero_name: str = hero_name

    @property
    def long_ago(self) -> int:
        return int(datetime.datetime.now(datetime.timezone.utc).timestamp()) - self.start_time

    async def get_twitch_data(self, twitch: TwitchClient) -> TwitchData:
        log.debug("`get_twitch_data` is starting")
        if self.twitch_id is None:
            return {
                "preview_url": const.PICTURE.LAVENDER640X360,
                "display_name": self.player_name,
                "url": "",
                "logo_url": const.Logo.dota,
                "vod_url": "",
                "twitch_status": "NoTwitch",
                "colour": const.MaterialPalette.gray(),
            }
        else:
            stream = await twitch.get_twitch_stream(self.twitch_id)
            if stream.online:
                twitch_status = "Live"
                vod_url = await twitch.last_vod_link(self.twitch_id, seconds_ago=self.long_ago)
                colour = const.Colour.prpl()
            else:
                twitch_status = "Offline"
                vod_url = ""
                colour = const.Colour.twitch()

            return {
                "preview_url": stream.preview_url,
                "display_name": stream.display_name,
                "url": stream.url,
                "logo_url": stream.logo_url,
                "vod_url": vod_url,
                "twitch_status": twitch_status,
                "colour": colour,
            }

    async def get_notification_image(self, twitch_data: TwitchData, colour: discord.Colour, bot: AluBot) -> Image.Image:
        log.debug("`get_notification_image` is starting")
        # prepare stuff for the following PIL procedures
        img = await bot.transposer.url_to_image(twitch_data["preview_url"])
        log.debug("`self.hero_ids` = %s", self.hero_ids)
        hero_image_urls = [await bot.dota_cache.hero.img_by_id(id) for id in self.hero_ids]
        log.debug("`hero_image_urls` = %s", hero_image_urls)
        hero_images = [await bot.transposer.url_to_image(url) for url in hero_image_urls]

        def build_notification_image() -> Image.Image:
            log.debug("`build_notification_image` is starting")
            width, height = img.size
            rectangle = Image.new("RGB", (width, 70), str(colour))
            ImageDraw.Draw(rectangle)
            img.paste(rectangle)

            # hero top-bar images
            for count, hero_image in enumerate(hero_images):
                hero_image = hero_image.resize((62, 35))
                hero_image = ImageOps.expand(
                    hero_image,
                    border=(0, 3, 0, 0),
                    fill=const.DOTA.PLAYER_COLOUR_MAP.get(count, "#FF0000"),
                )
                extra_space = 0 if count < 5 else 20
                img.paste(hero_image, (count * 62 + extra_space, 0))

            # middle text "Player - Hero"
            font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)
            draw = ImageDraw.Draw(img)
            text = f"{twitch_data['display_name']} - {self.hero_name}"
            w2, h2 = bot.transposer.get_text_wh(text, font)
            draw.text(((width - w2) / 2, 35), text, font=font, align="center")

            w2, h2 = bot.transposer.get_text_wh(text, font)
            draw.text(
                xy=(0, 35 + h2 + 10), text=twitch_data["twitch_status"], font=font, align="center", fill=str(colour)
            )
            return img

        return await asyncio.to_thread(build_notification_image)

    async def get_embed_and_file(self, bot: AluBot) -> tuple[discord.Embed, discord.File]:
        log.debug("Creating embed + file for Notification match")

        twitch_data = await self.get_twitch_data(bot.twitch)

        notification_image = await self.get_notification_image(twitch_data, twitch_data["colour"], bot)
        filename = (
            f'{twitch_data["twitch_status"]}-{twitch_data["display_name"].replace("_", "")}-'
            f'{(self.hero_name).replace(" ", "").replace(chr(39), "")}.png'  # chr39 is "'"
        )
        image_file = bot.transposer.image_to_file(notification_image, filename=filename)
        embed = (
            discord.Embed(
                colour=twitch_data["colour"],
                url=twitch_data["url"],
                description=(
                    f"`/match {self.match_id}` started {formats.human_timedelta(self.long_ago, strip=True)}\n"
                    f"{twitch_data['vod_url']}{self.links}"
                ),
            )
            .set_author(
                name=f"{twitch_data['display_name']} - {self.hero_name}",
                url=twitch_data["url"],
                icon_url=twitch_data["logo_url"],
            )
            .set_thumbnail(url=await bot.dota_cache.hero.img_by_id(self.hero_id))
            .set_image(url=f"attachment://{image_file.filename}")
            .set_footer(text=f"watch_server {self.server_steam_id}")
        )
        return embed, image_file


class PostMatchPlayerData(BasePostMatchPlayer):
    """
    Class
    """

    def __init__(
        self,
        *,
        player_data: dict,
        channel_id: int,
        message_id: int,
        api_calls_done: int,
    ):
        super().__init__(channel_id=channel_id, message_id=message_id)

        self.api_calls_done: int = api_calls_done

        self.match_id: int = player_data["match_id"]
        self.hero_id: int = player_data["hero_id"]
        self.outcome: str = "Win" if player_data["win"] else "Loss"  # todo: typing for player_data
        self.ability_upgrades_arr = player_data["ability_upgrades_arr"]
        self.items = [player_data[f"item_{i}"] for i in range(6)]
        self.kda = f'{player_data["kills"]}/{player_data["deaths"]}/{player_data["assists"]}'
        self.purchase_log: list = player_data["purchase_log"]
        self.aghanim_blessing = False
        self.aghanim_shard = False
        permanent_buffs = player_data["permanent_buffs"] or []  # [] if it is None
        for pb in permanent_buffs:
            if pb["permanent_buff"] == 12:
                self.aghanim_shard = True
            if pb["permanent_buff"] == 2:
                self.aghanim_blessing = True

    def __repr__(self) -> str:
        pairs = " ".join([f"{k}={v!r}" for k, v in self.__dict__.items()])
        return f"<{self.__class__.__name__} {pairs}>"

    @override
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour, bot: AluBot) -> Image.Image:
        img = await bot.transposer.url_to_image(embed_image_url)

        # items and aghanim shard/blessing
        async def get_item_timing(item_id: int) -> str:
            for purchase in reversed(self.purchase_log):
                if item_id == await bot.dota_cache.item.id_by_key(purchase["key"]):
                    self.purchase_log.remove(purchase)
                    return f"{math.ceil(purchase['time']/60)}m"
            return "?m"

        item_list: list[tuple[Image.Image, str]] = []
        for item_id in self.items:
            item_icon_url = await bot.dota_cache.item.icon_by_id(item_id)
            log.debug("item id %s %s", item_id, item_icon_url)
            image = await bot.transposer.url_to_image(item_icon_url)
            timing = await get_item_timing(item_id)
            item_list.append((image, timing))

        # reverse so we have proper order in the embed like
        # shard blessing item0 item1 item3 item4 item5 item6
        # because we will start drawing items from the end this way
        item_list = item_list[::-1]

        if self.aghanim_blessing:
            image = await bot.transposer.url_to_image(const.DOTA.lAZY_AGHS_BLESS)
            timing = await get_item_timing(271)
            item_list.append((image, timing))

        if self.aghanim_shard:
            image = await bot.transposer.url_to_image(const.DOTA.LAZY_AGHS_SHARD)
            timing = await get_item_timing(609)
            item_list.append((image, timing))

        # we only want first 18 image upgrades
        ability_icon_urls = [await bot.dota_cache.ability.icon_by_id(id) for id in self.ability_upgrades_arr[:18]]
        ability_icon_images = [await bot.transposer.url_to_image(url) for url in ability_icon_urls]

        talent_names = []
        for ability_upgrade in self.ability_upgrades_arr:
            talent_name = await bot.dota_cache.ability.talent_by_id(ability_upgrade)
            if talent_name is not None:
                talent_names.append(talent_name)

        def build_notification_image() -> Image.Image:
            width, height = img.size
            information_height = 50
            information_y = height - information_height
            rectangle = Image.new("RGB", (width, information_height), str(colour))
            ImageDraw.Draw(rectangle)
            img.paste(rectangle, (0, information_y))
            draw = ImageDraw.Draw(img)

            # items and aghanim shard/blessing
            font_item_timing = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 19)

            for count, (item_image, item_timing) in enumerate(item_list):
                # item image
                item_image = item_image.resize((69, information_height))  # 69/50 - to match 88/64 which is natural size
                left = width - (count + 1) * item_image.width
                img.paste(item_image, (left, height - item_image.height))

                # item timing
                item_timing_text_w, item_timing_text_h = bot.transposer.get_text_wh(item_timing, font_item_timing)
                draw.text((left, height - item_timing_text_h), item_timing, font=font_item_timing, align="left")

            # abilities
            ability_h = 37
            for count, ability_image in enumerate(ability_icon_images):
                ability_image = ability_image.resize((ability_h, ability_h))
                img.paste(ability_image, (count * ability_h, information_y - ability_image.height))

            # talents
            talent_font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 12)
            for count, talent_text in enumerate(talent_names):
                talent_text_w, talent_text_h = bot.transposer.get_text_wh(talent_text, talent_font)
                draw.text(
                    xy=(width - talent_text_w, information_y - 30 * 2 - 22 * count),
                    text=talent_text,
                    font=talent_font,
                    align="right",
                )

            # kda text
            font_kda = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)

            kda_text_w, kda_text_h = bot.transposer.get_text_wh(self.kda, font_kda)
            draw.text((0, height - kda_text_h - information_height - ability_h), self.kda, font=font_kda, align="right")

            # outcome text
            outcome_text_w, outcome_text_h = bot.transposer.get_text_wh(self.outcome, font_kda)
            colour_dict = {
                "Win": str(const.MaterialPalette.green(shade=800)),
                "Loss": str(const.MaterialPalette.red(shade=900)),
                "Not Scored": (255, 255, 255),
            }
            draw.text(
                xy=(0, height - kda_text_h - outcome_text_h - information_height - ability_h),
                text=self.outcome,
                font=font_kda,
                align="center",
                fill=colour_dict[self.outcome],
            )

            # img.show()
            return img

        return await asyncio.to_thread(build_notification_image)
