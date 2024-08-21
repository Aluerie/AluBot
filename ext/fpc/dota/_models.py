from __future__ import annotations

import asyncio
import datetime
import logging
import math
import re
from typing import TYPE_CHECKING, Literal, TypedDict, override

import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps

from utils import const, formats

from .._base import BaseMatchToEdit, BaseMatchToSend

if TYPE_CHECKING:
    from bot import AluBot
    from utils.dota import schemas


__all__ = ("MatchToSend", "StratzMatchToEdit", "NotCountedMatchToEdit")
type LiteralTwitchStatus = Literal["NoTwitch", "Offline", "Live"]


class TwitchData(TypedDict):
    preview_url: str
    display_name: str
    url: str
    logo_url: str
    vod_url: str
    twitch_status: LiteralTwitchStatus
    colour: discord.Colour


send_log = logging.getLogger("send_dota_fpc")
edit_log = logging.getLogger("edit_dota_fpc")


class MatchToSend(BaseMatchToSend):
    def __init__(
        self,
        bot: AluBot,
        *,
        match_id: int,
        friend_id: int,
        start_time: datetime.datetime,
        player_name: str,
        hero_id: int,
        hero_ids: list[int],
        server_steam_id: int,
        twitch_id: int | None = None,
        hero_name: str,
    ) -> None:
        super().__init__(bot)
        self.match_id: int = match_id
        self.friend_id: int = friend_id
        self.start_time: datetime.datetime = start_time
        self.player_name: str = player_name
        self.hero_id: int = hero_id
        self.hero_ids: list[int] = hero_ids
        self.server_steam_id: int = server_steam_id
        self.twitch_id: int | None = twitch_id
        self.hero_name: str = hero_name

    @property
    def links(self) -> str:
        """Markdown links to stats sites."""
        dotabuff = f"https://www.dotabuff.com/matches/{self.match_id}"
        opendota = f"https://www.opendota.com/matches/{self.match_id}"
        stratz = f"https://www.stratz.com/matches/{self.match_id}"
        return f"/[Dbuff]({dotabuff})/[Odota]({opendota})/[Stratz]({stratz})"

    @property
    def long_ago(self) -> int:
        now = datetime.datetime.now(datetime.UTC)
        return (now - self.start_time).seconds

    async def get_twitch_data(self) -> TwitchData:
        send_log.debug("`get_twitch_data` is starting")
        if self.twitch_id is None:
            return {
                "preview_url": const.Picture.Placeholder640X360,
                "display_name": self.player_name,
                "url": "",
                "logo_url": const.Logo.Dota,
                "vod_url": "",
                "twitch_status": "NoTwitch",
                "colour": const.MaterialPalette.gray(),
            }
        else:
            streamer = await self.bot.twitch.fetch_streamer(self.twitch_id)
            if streamer.live:
                twitch_status = "Live"
                vod_url = await streamer.vod_link(seconds_ago=self.long_ago)
                colour = discord.Colour(const.Colour.blueviolet)
            else:
                twitch_status = "Offline"
                vod_url = ""
                colour = discord.Colour(const.Colour.twitch)

            return {
                "preview_url": streamer.preview_url,
                "display_name": streamer.display_name,
                "url": streamer.url,
                "logo_url": streamer.avatar_url,
                "vod_url": vod_url,
                "twitch_status": twitch_status,
                "colour": colour,
            }

    @override
    async def notification_image(self, twitch_data: TwitchData, colour: discord.Colour) -> Image.Image:
        send_log.debug("`get_notification_image` is starting")
        # prepare stuff for the following PIL procedures
        canvas = await self.bot.transposer.url_to_image(twitch_data["preview_url"])
        hero_image_urls = [await self.bot.cache_dota.hero.img_by_id(id) for id in self.hero_ids]
        hero_images = [await self.bot.transposer.url_to_image(url) for url in hero_image_urls]

        def build_notification_image() -> Image.Image:
            """Image Builder."""
            send_log.debug("`build_notification_image` is starting")

            canvas_w, canvas_h = canvas.size
            draw = ImageDraw.Draw(canvas)

            topbar_h = 70

            def draw_picked_heroes() -> None:
                """Draw picked heroes in the match."""
                rectangle = Image.new("RGB", (canvas_w, topbar_h), str(colour))
                ImageDraw.Draw(rectangle)
                canvas.paste(rectangle)

                hero_w, hero_h = (62, 35)
                for count, img in enumerate(hero_images):
                    img = img.resize((hero_w, hero_h))
                    img = ImageOps.expand(img, border=(0, 3, 0, 0), fill=const.Dota.PLAYER_COLOUR_MAP[count])
                    extra_space = 0 if count < 5 else 20  # math 640 - 62 * 10 = 20 where 640 is initial resolution.
                    canvas.paste(img, (count * hero_w + extra_space, 0))

            draw_picked_heroes()

            def draw_player_hero_text() -> None:
                """Draw "Player - Hero" text in the middle."""
                font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)

                text = f"{twitch_data['display_name']} - {self.hero_name}"
                w, h = self.bot.transposer.get_text_wh(text, font)
                draw.text(((canvas_w - w) / 2, 35), text, font=font, align="center")

            draw_player_hero_text()

            def draw_twitch_status() -> None:
                """Write twitch status, like Live / Offline / NoTwitch."""
                font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 13)
                text = twitch_data["twitch_status"]
                w, h = self.bot.transposer.get_text_wh(text, font)
                draw.text(xy=(canvas_w - w, topbar_h + 1 + h), text=text, font=font, fill=str(colour))

            draw_twitch_status()

            return canvas

        return await asyncio.to_thread(build_notification_image)

    @override
    async def embed_and_file(self) -> tuple[discord.Embed, discord.File]:
        send_log.debug("Creating embed + file for Notification match")

        twitch_data = await self.get_twitch_data()

        notification_image = await self.notification_image(twitch_data, twitch_data["colour"])
        title = f"{twitch_data['display_name']} - {self.hero_name}"
        filename = twitch_data["twitch_status"] + "-" + re.sub(r"[_' ]", "", title) + ".png"
        image_file = self.bot.transposer.image_to_file(notification_image, filename=filename)
        hero_emoji = getattr(const.DotaHeroes, await self.bot.cache_dota.hero.alias_by_id(self.hero_id))
        embed = (
            discord.Embed(
                colour=twitch_data["colour"],
                title=f"{title} {hero_emoji}",
                url=twitch_data["url"],
                description=(
                    f"`/match {self.match_id}` started {formats.human_timedelta(self.long_ago, mode='strip')}\n"
                    f"{twitch_data['vod_url']}{self.links}"
                ),
            )
            .set_author(name=title, url=twitch_data["url"], icon_url=twitch_data["logo_url"])
            .set_thumbnail(url=await self.bot.cache_dota.hero.img_by_id(self.hero_id))
            .set_image(url=f"attachment://{image_file.filename}")
            .set_footer(text=f"watch_server {self.server_steam_id}")
        )  # | dota2://matchid={self.match_id}&matchtime={matchtime}") # but it's not really convenient.
        return embed, image_file

    @override
    async def insert_into_game_messages(self, message_id: int, channel_id: int) -> None:
        query = """
            INSERT INTO dota_messages (message_id, channel_id, match_id, friend_id, hero_id, player_name)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        await self.bot.pool.execute(
            query, message_id, channel_id, self.match_id, self.friend_id, self.hero_id, self.player_name
        )


class StratzMatchToEdit(BaseMatchToEdit):
    """Class."""

    def __init__(
        self,
        bot: AluBot,
        data: schemas.StratzGraphQL.GetFPCMatchToEdit.ResponseDict,
    ) -> None:
        super().__init__(bot)

        player = data["data"]["match"]["players"][0]

        self.hero_id: int = player["heroId"]
        self.outcome: str = "Win" if player["isVictory"] else "Loss"
        self.kda: str = f'{player["kills"]}/{player["deaths"]}/{player["assists"]}'

        self.ability_upgrades_ids: list[int] = [
            event["abilityId"] for event in player["playbackData"]["abilityLearnEvents"][:18]
        ]

        item_ids: list[int] = [player[f"item{i}Id"] or 0 for i in range(6)]

        for buff_event in player["stats"]["matchPlayerBuffEvent"]:
            item_id = buff_event.get("itemId")
            if item_id:
                if item_id == const.Dota.AGHANIMS_SCEPTER_ITEM_ID:
                    # Stratz writes it like it's buff from aghs when it's a buff from a blessing, idk
                    item_ids.append(const.Dota.AGHANIMS_BLESSING_ITEM_ID)
                else:
                    item_ids.append(item_id)

        self.sorted_item_purchases: list[tuple[int, str]] = []
        for purchase_event in reversed(player["playbackData"]["purchaseEvents"]):
            item_id = purchase_event["itemId"]
            if item_id in item_ids:
                self.sorted_item_purchases.append((item_id, f"{math.ceil(purchase_event['time']/60)}m"))
                item_ids.remove(item_id)

        self.sorted_item_purchases.reverse()  # reverse back
        # add items for which we couldn't find item timings back
        # this happens either bcs it was free (shard from tormentor) or Stratz API failed to parse properly.
        self.sorted_item_purchases.extend([(item_id, "") for item_id in item_ids])

        self.neutral_item_id: int = player["neutral0Id"] or 0

        self.facet: int = player["variant"]

    @override
    def __repr__(self) -> str:
        pairs = " ".join([f"{k}={v!r}" for k, v in self.__dict__.items()])
        return f"<{self.__class__.__name__} {pairs}>"

    @override
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour) -> Image.Image:
        canvas = await self.bot.transposer.url_to_image(embed_image_url)
        item_icon_urls = [await self.bot.cache_dota.item.icon_by_id(id) for id, _ in self.sorted_item_purchases]
        item_icon_images = [await self.bot.transposer.url_to_image(url) for url in item_icon_urls]

        neutral_item_url = await self.bot.cache_dota.item.icon_by_id(self.neutral_item_id)
        neutral_item_image = await self.bot.transposer.url_to_image(neutral_item_url)

        ability_icon_urls = [
            await self.bot.cache_dota.hero.ability_icon_by_ability_id(id) for id in self.ability_upgrades_ids
        ]
        ability_icon_images = [await self.bot.transposer.url_to_image(url) for url in ability_icon_urls]

        hero_talents = await self.bot.cache_dota.hero.talents_by_id(self.hero_id)
        talent_ids = [talent[0] for talent in hero_talents]

        talents_order = [
            ability_upgrade for ability_upgrade in self.ability_upgrades_ids if ability_upgrade in talent_ids
        ]

        facet = await self.bot.cache_dota.hero.facets_by_id(self.hero_id, self.facet)
        facet_image = await self.bot.transposer.url_to_image(facet["icon"])

        def build_notification_image() -> Image.Image:
            edit_log.debug("Building edited notification message.")
            canvas_w, canvas_h = canvas.size
            draw = ImageDraw.Draw(canvas)

            def draw_items_row() -> float:
                """Draw items on a single row.

                Returns height of the row to align other elements in the canvas.
                """
                h = 50  # the height for items row, meaning items themselves are of this height.
                item_w = 69  # then item_w, item_h is (69, 50) which matches 88/64 in proportion (original size).
                font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 19)  # font for item timings

                # rectangle for the row
                rectangle = Image.new("RGB", (canvas_w, h), str(colour))
                ImageDraw.Draw(rectangle)
                canvas.paste(rectangle, (0, canvas_h - h))

                # item images
                for count, img in enumerate(item_icon_images):
                    canvas.paste(img.resize((item_w, h)), (count * item_w, canvas_h - h))

                # item timings
                for count, (item_id, item_timing) in enumerate(self.sorted_item_purchases):
                    if item_timing:
                        text_w, text_h = self.bot.transposer.get_text_wh(item_timing, font)
                        draw.text((count * item_w, canvas_h - text_h), item_timing, font=font, align="left")

                canvas.paste(im=neutral_item_image.resize((item_w, h)), box=(canvas_w - item_w, canvas_h - h))
                return h

            items_h = draw_items_row()

            def draw_abilities_row() -> float:
                """Draw row representing the order of abilities in skill order of the player."""
                h = 37

                for count, img in enumerate(ability_icon_images):
                    canvas.paste(img.resize((h, h)), (count * h, canvas_h - items_h - h))
                return h

            abilities_h = draw_abilities_row()

            def draw_kda() -> float:
                """Draw kda.

                Returns height of the segment.
                """
                font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)
                w, h = self.bot.transposer.get_text_wh(self.kda, font)
                draw.text((0, canvas_h - items_h - abilities_h - h), self.kda, font=font)
                return h

            kda_h = draw_kda()

            def draw_outcome() -> float:
                """Draw outcome of the game (Win or Loss).

                Returns height of the segment.
                """
                font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)
                w, h = self.bot.transposer.get_text_wh(self.outcome, font)
                colour_map = {
                    "Win": str(const.MaterialPalette.green(shade=800)),
                    "Loss": str(const.MaterialPalette.red(shade=900)),
                    "Not Scored": (255, 255, 255),
                }
                draw.text(
                    xy=(0, canvas_h - items_h - abilities_h - kda_h - h),
                    text=self.outcome,
                    font=font,
                    fill=colour_map[self.outcome],
                )
                return h

            outcome_h = draw_outcome()

            def draw_talent_tree_choices() -> None:
                """Draw talent tree choices.

                Mirrors hero's talent tree. Chosen talents are marked with orange colour (otherwise black).
                Draws mono-colour rectangles on the left/right side of the image.
                """
                font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 15)
                p = 6

                for count, (talent_id, talent_display_text) in enumerate(hero_talents):
                    text_w, text_h = self.bot.transposer.get_text_wh(talent_display_text, font)

                    x = 0 if count % 2 else canvas_w - text_w
                    position = (x, canvas_h - items_h - abilities_h - kda_h - outcome_h - 20 - 26 * (count // 2))
                    x, y, u, v = draw.textbbox(position, talent_display_text, font=font)

                    if talent_id in talents_order[:4]:
                        fill_colour = "darkorange"
                    elif talent_id in talents_order[4:]:
                        fill_colour = "gray"
                    else:
                        fill_colour = "black"

                    draw.rectangle(xy=(x - p, y - p, u + p, v + p), fill=fill_colour)
                    draw.text(xy=position, text=talent_display_text, font=font, align="right")

            draw_talent_tree_choices()

            def draw_facet() -> None:
                """Draw facet icon+rectangle. Just a mono-colour rectangle with icon and title text."""
                icon_h = 40
                icon_p = 1
                text_p = 8  # currently just left, right
                font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 22)

                # text + rectangle
                text_w, text_h = self.bot.transposer.get_text_wh(facet["title"], font)
                x, y, u, v = (
                    canvas_w - text_w - icon_h - 2 * text_p,
                    canvas_h - items_h - abilities_h - icon_h,
                    canvas_w,
                    canvas_h - items_h - abilities_h,
                )
                draw.rectangle(xy=(x, y, u, v), fill=facet["colour"])
                draw.text((x + icon_h + text_p, v - (icon_h + text_h) / 2), facet["title"], font=font)

                # icon
                resized_facet_image = facet_image.resize((icon_h - icon_p, icon_h - icon_p))
                canvas.paste(resized_facet_image, (x + icon_p, y + icon_p), mask=resized_facet_image)

            draw_facet()

            # img.show()
            return canvas

        return await asyncio.to_thread(build_notification_image)


class NotCountedMatchToEdit(BaseMatchToEdit):
    """Class."""

    @override
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour) -> Image.Image:
        img = await self.bot.transposer.url_to_image(embed_image_url)

        def build_notification_image() -> Image.Image:
            edit_log.debug("Building edited notification message.")
            width, height = img.size

            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 45)
            text = "Not Counted"
            text_w, text_h = self.bot.transposer.get_text_wh(text, font)
            draw.text(
                xy=(0, height - text_h), text=text, font=font, align="left", fill=str(discord.Colour.dark_orange())
            )

            # img.show()
            return img

        return await asyncio.to_thread(build_notification_image)


if TYPE_CHECKING:
    from utils import AluCog

    # BETA TESTING USAGE
    # from .fpc.dota._models import beta_test_stratz_edit
    # await beta_test_stratz_edit(self)


async def beta_test_stratz_edit(self: AluCog) -> None:
    """Testing function for `edit_notification_image` from LoL's MatchToEdit class.

    Import this into `beta_task` for easy testing of how new elements alignment.
    """
    from ext.fpc.dota._models import StratzMatchToEdit

    await self.bot.initialize_dota_pulsefire_clients()
    self.bot.initialize_cache_dota()

    match_id = 7769171805
    friend_id = 321580662
    data = await self.bot.stratz.get_fpc_match_to_edit(match_id=match_id, friend_id=friend_id)

    match_to_edit = StratzMatchToEdit(self.bot, data)

    new_image = await match_to_edit.edit_notification_image(const.Picture.Placeholder640X360, discord.Colour.purple())
    new_image.show()
