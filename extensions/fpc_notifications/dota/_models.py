from __future__ import annotations

import asyncio
import datetime
import logging
import math
from typing import TYPE_CHECKING, Literal, Optional, TypedDict, override

import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps

from utils import const, dota, formats

from .._fpc_utils import BaseMatchToEdit, BaseMatchToSend

if TYPE_CHECKING:
    from bot import AluBot
    from utils.dota import schemas


__all__ = (
    "DotaFPCMatchToSend",
    "DotaFPCMatchToEditWithOpenDota",
    "DotaFPCMatchToEditWithStratz",
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


class DotaFPCMatchToSend(BaseMatchToSend):
    def __init__(
        self,
        bot: AluBot,
        *,
        match_id: int,
        friend_id: int,
        start_time: int,
        player_name: str,
        hero_id: int,
        hero_ids: list[int],
        server_steam_id: int,
        twitch_id: Optional[int] = None,
        hero_name: str,
    ):
        super().__init__(bot)
        self.match_id: int = match_id
        self.friend_id: int = friend_id
        self.start_time: int = start_time
        self.player_name: str = player_name
        self.hero_id: int = hero_id
        self.hero_ids: list[int] = hero_ids
        self.server_steam_id: int = server_steam_id
        self.twitch_id: Optional[int] = twitch_id
        self.hero_name: str = hero_name

    @property
    def links(self) -> str:
        """Links to stats sites in markdown format."""
        dotabuff = f"https://www.dotabuff.com/matches/{self.match_id}"
        opendota = f"https://www.opendota.com/matches/{self.match_id}"
        stratz = f"https://www.stratz.com/matches/{self.match_id}"
        return f"/[Dbuff]({dotabuff})/[Odota]({opendota})/[Stratz]({stratz})"

    @property
    def long_ago(self) -> int:
        return int(datetime.datetime.now(datetime.timezone.utc).timestamp()) - self.start_time

    async def get_twitch_data(self) -> TwitchData:
        log.debug("`get_twitch_data` is starting")
        if self.twitch_id is None:
            return {
                "preview_url": const.PICTURE.PLACEHOLDER640X360,
                "display_name": self.player_name,
                "url": "",
                "logo_url": const.Logo.dota,
                "vod_url": "",
                "twitch_status": "NoTwitch",
                "colour": const.MaterialPalette.gray(),
            }
        else:
            stream = await self.bot.twitch.get_twitch_stream(self.twitch_id)
            if stream.online:
                twitch_status = "Live"
                vod_url = await self.bot.twitch.last_vod_link(self.twitch_id, seconds_ago=self.long_ago)
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

    async def get_notification_image(self, twitch_data: TwitchData, colour: discord.Colour) -> Image.Image:
        log.debug("`get_notification_image` is starting")
        # prepare stuff for the following PIL procedures
        img = await self.bot.bot.transposer.url_to_image(twitch_data["preview_url"])
        hero_image_urls = [await self.bot.bot.dota_cache.hero.img_by_id(id) for id in self.hero_ids]
        hero_images = [await self.bot.bot.transposer.url_to_image(url) for url in hero_image_urls]

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
            w2, h2 = self.bot.bot.transposer.get_text_wh(text, font)
            draw.text(((width - w2) / 2, 35), text, font=font, align="center")

            w2, h2 = self.bot.bot.transposer.get_text_wh(text, font)
            draw.text(
                xy=(0, 35 + h2 + 10), text=twitch_data["twitch_status"], font=font, align="center", fill=str(colour)
            )
            return img

        return await asyncio.to_thread(build_notification_image)

    @override
    async def get_embed_and_file(self) -> tuple[discord.Embed, discord.File]:
        log.debug("Creating embed + file for Notification match")

        twitch_data = await self.get_twitch_data()

        notification_image = await self.get_notification_image(twitch_data, twitch_data["colour"])
        filename = (
            f'{twitch_data["twitch_status"]}-{twitch_data["display_name"].replace("_", "")}-'
            f'{(self.hero_name).replace(" ", "").replace(chr(39), "")}.png'  # chr39 is "'"
        )
        image_file = self.bot.transposer.image_to_file(notification_image, filename=filename)
        embed = (
            discord.Embed(
                colour=twitch_data["colour"],
                title=f"{twitch_data['display_name']} - {self.hero_name}",
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
            .set_thumbnail(url=await self.bot.dota_cache.hero.img_by_id(self.hero_id))
            .set_image(url=f"attachment://{image_file.filename}")
            # dota2://matchid also can take "&matchtime={matchtime}"
            .set_footer(text=f"watch_server {self.server_steam_id} | dota2://matchid={self.match_id}")
        )
        return embed, image_file

    @override
    async def insert_into_game_messages(self, message_id: int, channel_id: int):
        query = """
            INSERT INTO dota_messages (message_id, channel_id, match_id, friend_id, hero_id) 
            VALUES ($1, $2, $3, $4, $5)
        """
        await self.bot.pool.execute(query, message_id, channel_id, self.match_id, self.friend_id, self.hero_id)


class DotaFPCMatchToEditWithOpenDota(BaseMatchToEdit):
    """
    Class
    """

    def __init__(
        self,
        bot: AluBot,
        *,
        player: dota.OpenDotaAPISchema.Player,
    ):
        super().__init__(bot)

        self.outcome: str = "Win" if player["win"] else "Loss"
        self.kda: str = f'{player["kills"]}/{player["deaths"]}/{player["assists"]}'

        self.ability_upgrades_ids: list[int] = player["ability_upgrades_arr"][:18]

        self.item_ids: list[int] = [player[f"item_{i}"] for i in range(6)]
        if player["aghanims_shard"]:
            self.item_ids.append(const.DOTA.AGHANIMS_SHARD_ITEM_ID)
        if player["aghanims_scepter"]:
            self.item_ids.append(const.DOTA.AGHANIMS_BLESSING_ITEM_ID)

        self.neutral_item_id: int = player["item_neutral"]

    def __repr__(self) -> str:
        pairs = " ".join([f"{k}={v!r}" for k, v in self.__dict__.items()])
        return f"<{self.__class__.__name__} {pairs}>"

    @override
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour) -> Image.Image:
        img = await self.bot.transposer.url_to_image(embed_image_url)

        item_icon_urls = [await self.bot.dota_cache.item.icon_by_id(item_id) for item_id in self.item_ids]
        item_icon_images = [await self.bot.transposer.url_to_image(url) for url in item_icon_urls]

        neutral_item_url = await self.bot.dota_cache.item.icon_by_id(self.neutral_item_id)
        neutral_item_image = await self.bot.transposer.url_to_image(neutral_item_url)

        ability_icon_urls = [await self.bot.dota_cache.ability.icon_by_id(id) for id in self.ability_upgrades_ids]
        ability_icon_images = [await self.bot.transposer.url_to_image(url) for url in ability_icon_urls]

        talent_names = []
        for ability_upgrade in self.ability_upgrades_ids:
            talent_name = await self.bot.dota_cache.ability.talent_by_id(ability_upgrade)
            if talent_name is not None:
                talent_names.append(talent_name)

        def build_notification_image() -> Image.Image:
            log.debug("Building edited notification message.")
            width, height = img.size
            information_height = 50
            rectangle = Image.new("RGB", (width, information_height), str(colour))
            ImageDraw.Draw(rectangle)
            img.paste(rectangle, (0, height - information_height))
            draw = ImageDraw.Draw(img)

            for count, item_image in enumerate(item_icon_images):
                # item image
                item_image = item_image.resize((69, information_height))  # 69/50 - to match 88/64 which is natural size
                left = count * item_image.width
                img.paste(item_image, (left, height - item_image.height))

            resized_neutral_item_image = i = neutral_item_image.resize((69, information_height))
            img.paste(im=i, box=(width - i.width, height - i.height))

            # abilities
            ability_h = 37
            for count, ability_image in enumerate(ability_icon_images):
                ability_image = ability_image.resize((ability_h, ability_h))
                img.paste(ability_image, (count * ability_h, height - information_height - ability_image.height))

            # talents
            talent_font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 12)
            for count, talent_text in enumerate(talent_names):
                talent_text_w, talent_text_h = self.bot.transposer.get_text_wh(talent_text, talent_font)
                draw.text(
                    xy=(width - talent_text_w, height - information_height - 30 * 2 - 22 * count),
                    text=talent_text,
                    font=talent_font,
                    align="right",
                )

            # kda text
            font_kda = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)

            kda_text_w, kda_text_h = self.bot.transposer.get_text_wh(self.kda, font_kda)
            draw.text((0, height - kda_text_h - information_height - ability_h), self.kda, font=font_kda, align="right")

            # outcome text
            outcome_text_w, outcome_text_h = self.bot.transposer.get_text_wh(self.outcome, font_kda)
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


class DotaFPCMatchToEditWithStratz(BaseMatchToEdit):
    """
    Class
    """

    def __init__(
        self,
        bot: AluBot,
        *,
        data: schemas.StratzGraphQLQueriesSchema.GetFPCMatchToEdit.ResponseDict,
    ):
        super().__init__(bot)

        player = data["data"]["match"]["players"][0]

        item_ids: list[int] = [player[f"item{i}Id"] for i in range(6)]

        for buff_event in player["stats"]["matchPlayerBuffEvent"]:
            item_id = buff_event.get("itemId")
            if item_id:
                item_ids.append(item_id)

        self.sorted_item_purchases: list[tuple[int, str]] = []
        for purchase_event in reversed(player["playbackData"]["purchaseEvents"]):
            item_id = purchase_event["itemId"]
            if item_id in item_ids:
                self.sorted_item_purchases.append((item_id, f"{math.ceil(purchase_event['time']/60)}m"))
                item_ids.remove(item_id)

        self.sorted_item_purchases.reverse()  # reverse back
        self.sorted_item_purchases.extend([(item_id, "") for item_id in item_ids])

        self.neutral_item_id: int = player["neutral0Id"]

    def __repr__(self) -> str:
        pairs = " ".join([f"{k}={v!r}" for k, v in self.__dict__.items()])
        return f"<{self.__class__.__name__} {pairs}>"

    @override
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour) -> Image.Image:
        img = await self.bot.transposer.url_to_image(embed_image_url)
        item_icon_urls = [await self.bot.dota_cache.item.icon_by_id(id) for id, timing in self.sorted_item_purchases]
        item_icon_images = [await self.bot.transposer.url_to_image(url) for url in item_icon_urls]

        neutral_item_url = await self.bot.dota_cache.item.icon_by_id(self.neutral_item_id)
        neutral_item_image = await self.bot.transposer.url_to_image(neutral_item_url)

        def build_notification_image() -> Image.Image:
            log.debug("Building edited notification message.")
            width, height = img.size

            information_height = 50
            rectangle = Image.new("RGB", (width, information_height), str(colour))
            ImageDraw.Draw(rectangle)
            img.paste(rectangle, (0, height - information_height))
            draw = ImageDraw.Draw(img)

            for count, item_image in enumerate(item_icon_images):
                # item image
                item_image = item_image.resize((69, information_height))  # 69/50 - to match 88/64 which is natural size
                left = count * item_image.width
                img.paste(item_image, (left, height - item_image.height))

            # items and aghanim shard/blessing
            font_item_timing = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 19)

            for count, (item_id, item_timing) in enumerate(self.sorted_item_purchases):
                if item_timing:
                    # item timing
                    left = count * 69
                    item_timing_w, item_timing_h = self.bot.transposer.get_text_wh(item_timing, font_item_timing)
                    draw.text((left, height - item_timing_h), item_timing, font=font_item_timing, align="left")

            resized_neutral_item_image = i = neutral_item_image.resize((69, information_height))
            img.paste(im=i, box=(width - i.width, height - i.height))

            # img.show()
            return img

        return await asyncio.to_thread(build_notification_image)


class DotaFPCMatchToEditNotCounted(BaseMatchToEdit):
    """
    Class
    """

    def __init__(self, bot: AluBot):
        super().__init__(bot)

    @override
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour) -> Image.Image:
        img = await self.bot.transposer.url_to_image(embed_image_url)

        def build_notification_image() -> Image.Image:
            log.debug("Building edited notification message.")
            width, height = img.size

            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)
            text = "Not Counted"
            text_w, text_h = self.bot.transposer.get_text_wh(text, font)
            draw.text(xy=(0, height - text_h), text=text, font=font, align="left")

            # img.show()
            return img

        return await asyncio.to_thread(build_notification_image)


if TYPE_CHECKING:
    from utils import AluCog


async def beta_test_stratz_edit(self: AluCog):
    """Testing function for `edit_notification_image` from LoLFPCMatchToEdit class

    Import this into `beta_task` for easy testing of how new elements alignment.
    """
    # BETA TESTING USAGE
    # from .fpc_notifications.dota._models import beta_test_stratz_edit
    # await beta_test_stratz_edit(self)

    from extensions.fpc_notifications.dota._models import DotaFPCMatchToEditWithStratz

    await self.bot.initialize_dota_pulsefire_clients()
    self.bot.initialize_dota_cache()

    match_id = 7549006442
    friend_id = 159020918
    data = await self.bot.stratz_client.get_fpc_match_to_edit(match_id=match_id, friend_id=friend_id)

    match_to_edit = DotaFPCMatchToEditWithStratz(self.bot, data=data)

    new_image = await match_to_edit.edit_notification_image(const.PICTURE.PLACEHOLDER640X360, discord.Colour.purple())
    # new_image.show()
    return new_image
