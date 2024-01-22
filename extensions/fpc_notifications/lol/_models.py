from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, Optional, override

import discord
from PIL import Image, ImageDraw, ImageFont

from utils import const, lol
from utils.formats import human_timedelta

from .._fpc_utils import BaseMatchToEdit, BaseMatchToSend

if TYPE_CHECKING:
    from pulsefire.schemas import RiotAPISchema

    from bot import AluBot


__all__ = (
    "LoLFPCMatchToSend",
    "LoLFPCMatchToEdit",
)


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def lol_links(platform: lol.LiteralPlatform, game_name: str, tag_line: str) -> str:
    opgg = f"https://op.gg/summoners/{lol.PLATFORM_TO_SERVER[platform]}/{game_name}-{tag_line}"
    ugg = f"https://u.gg/lol/profile/{platform}/{game_name}-{tag_line}"
    return f"/[Opgg]({opgg})/[Ugg]({ugg})"


class LoLFPCMatchToSend(BaseMatchToSend):
    def __init__(
        self,
        bot: AluBot,
        *,
        match_id: int,
        platform: lol.LiteralPlatform,
        game_name: str,
        tag_line: str,
        start_time: int,
        champion_id: int,
        all_champion_ids: list[int],
        twitch_id: int,
        summoner_spell_ids: tuple[int, int],
        rune_ids: list[int],
        summoner_id: str,
    ):
        super().__init__(bot)

        self.platform: lol.LiteralPlatform = platform
        self.game_name: str = game_name
        self.tag_line: str = tag_line

        self.match_id: int = match_id
        self.start_time: int = start_time
        self.champion_id: int = champion_id
        self.all_champion_ids: list[int] = all_champion_ids
        self.twitch_id: int = twitch_id
        self.summoner_spell_ids: tuple[int, int] = summoner_spell_ids
        self.rune_ids: list[int] = rune_ids
        self.summoner_id: str = summoner_id

    @property
    def links(self) -> str:
        """Links to stats sites in markdown format."""
        return lol_links(self.platform, self.game_name, self.tag_line)

    @property
    def long_ago(self) -> int:
        """Gives how many seconds passed from start time till Now"""
        if self.start_time == 0:
            # start_time is filled later in Riot Web API (after loading screen)
            # thus sometimes it gonna be just plain zero when we find the match during the loading screen
            # so let's just return 0 as in "Now"
            return 0

        timestamp_seconds = round(self.start_time / 1000)  # the `self.start_time` is given in milliseconds
        return int(datetime.datetime.now(datetime.timezone.utc).timestamp() - timestamp_seconds)

    async def get_notification_image(
        self,
        stream_preview_url: str,
        display_name: str,
        champion_name: str,
    ) -> Image.Image:
        # prepare stuff for the following PIL procedures
        img = await self.bot.transposer.url_to_image(stream_preview_url)
        sorted_champion_ids = await self.bot.meraki_roles.sort_champions_by_roles(self.all_champion_ids)
        champion_icon_urls = [await self.bot.cdragon.champion.icon_by_id(id) for id in sorted_champion_ids]
        champion_icon_images = [await self.bot.transposer.url_to_image(url) for url in champion_icon_urls]
        rune_icon_urls = [await self.bot.cdragon.rune.icon_by_id(id) for id in self.rune_ids]
        rune_icon_images = [await self.bot.transposer.url_to_image(url) for url in rune_icon_urls]
        summoner_icon_urls = [await self.bot.cdragon.summoner_spell.icon_by_id(id) for id in self.summoner_spell_ids]
        summoner_icon_images = [await self.bot.transposer.url_to_image(url) for url in summoner_icon_urls]

        def build_notification_image() -> Image.Image:
            width, height = img.size
            information_row = 50
            rectangle = Image.new("RGB", (width, 100), str(const.Colour.rspbrry()))
            ImageDraw.Draw(rectangle)
            img.paste(rectangle)
            img.paste(rectangle, (0, height - information_row))

            # champion icons
            for count, champion_image in enumerate(champion_icon_images):
                champion_image = champion_image.resize((62, 62))
                extra_space = 0 if count < 5 else 20
                img.paste(champion_image, (count * 62 + extra_space, 0))

            # middle text "Streamer - Champion"
            font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)
            draw = ImageDraw.Draw(img)
            text = f"{display_name} - {champion_name}"
            w2, h2 = self.bot.transposer.get_text_wh(text, font)
            draw.text(xy=((width - w2) / 2, 65), text=text, font=font, align="center")

            # rune icons
            left = 0
            for count, rune_image in enumerate(rune_icon_images):
                if count < 6:
                    # actual runes (as in non-stat modifiers)
                    rune_image = rune_image.resize((information_row, information_row))
                img.paste(rune_image, (left, height - rune_image.height), rune_image)
                left += rune_image.width

            # summoner spell icons
            left = width - 2 * information_row
            for count, spell_image in enumerate(summoner_icon_images):
                spell_image = spell_image.resize((information_row, information_row))
                img.paste(spell_image, (left + count * spell_image.width, height - spell_image.height))
            return img

        return await asyncio.to_thread(build_notification_image)

    async def get_embed_and_file(self) -> tuple[discord.Embed, discord.File]:
        stream = await self.bot.twitch.get_twitch_stream(self.twitch_id)
        champion_name = await self.bot.cdragon.champion.name_by_id(self.champion_id)

        notification_image = await self.get_notification_image(stream.preview_url, stream.display_name, champion_name)

        filename = f'{stream.display_name.replace("_", "")}-playing-{champion_name}.png'
        image_file = self.bot.transposer.image_to_file(notification_image, filename=filename)

        embed = discord.Embed(color=const.Colour.rspbrry(), url=stream.url)
        embed.description = (
            f"Match `{self.platform.upper()}_{self.match_id}` started {human_timedelta(self.long_ago, strip=True)}\n"
            f"{await self.bot.twitch.last_vod_link(stream.twitch_id, seconds_ago=self.long_ago)}{self.links}"
        )
        embed.set_image(url=f"attachment://{image_file.filename}")
        embed.set_thumbnail(url=await self.bot.cdragon.champion.icon_by_id(self.champion_id))
        embed.set_author(name=f"{stream.display_name} - {champion_name}", url=stream.url, icon_url=stream.logo_url)
        return embed, image_file

    @override
    async def insert_into_game_messages(self, message_id: int, channel_id: int):
        query = """
            INSERT INTO lol_messages
            (message_id, channel_id, match_id, platform, champion_id) 
            VALUES ($1, $2, $3, $4, $5)
        """
        await self.bot.pool.execute(query, message_id, channel_id, self.match_id, self.platform, self.champion_id)

        query = "UPDATE lol_accounts SET last_edited=$1 WHERE summoner_id=$2"
        await self.bot.pool.execute(query, self.match_id, self.summoner_id)


class LoLFPCMatchToEdit(BaseMatchToEdit):
    def __init__(
        self,
        bot: AluBot,
        *,
        participant: RiotAPISchema.LolMatchV5MatchInfoParticipant,
        timeline: RiotAPISchema.LolMatchV5MatchTimeline,
    ):
        super().__init__(bot)

        self.summoner_id: str = participant["summonerId"]
        self.kda: str = f"{participant['kills']}/{participant['deaths']}/{participant['assists']}"
        self.outcome: str = "Win" if participant["win"] else "Loss"

        self.trinket_item_id: int = participant["item6"]

        self.skill_build: list[int] = []  # list of 1, 2, 3, 4 numbers which correspond to Q, W, E, R skill build order

        item_ids: list[int] = [participant[f"item{i}"] for i in range(0, 5 + 1)]
        self.sorted_item_ids: list[int] = []

        for frame in reversed(timeline["info"]["frames"]):
            for event in frame["events"]:
                if not event.get("participantId") == participant["participantId"]:
                    # not our player
                    continue

                match event["type"]:
                    # SKILL BUILD
                    case "SKILL_LEVEL_UP":
                        skill_slot = event.get("skillSlot")  # .get only bcs of NotRequired type-hinting
                        if skill_slot:
                            self.skill_build.append(skill_slot)

                    # ITEM ORDER
                    case "ITEM_PURCHASED":
                        item_id = event.get("itemId")
                        if item_id and item_id in item_ids:
                            self.sorted_item_ids.append(item_id)
                            item_ids.remove(item_id)

    @override
    async def edit_notification_image(self, embed_image_url: str, _colour: discord.Colour) -> Image.Image:
        img = await self.bot.transposer.url_to_image(embed_image_url)
        item_icon_urls = [await self.bot.cdragon.item.icon_by_id(id) for id in reversed(self.sorted_item_ids) if id]
        item_icon_images = [await self.bot.transposer.url_to_image(url) for url in item_icon_urls]

        trinket_icon_url = await self.bot.cdragon.item.icon_by_id(self.trinket_item_id)
        trinket_icon_img = await self.bot.transposer.url_to_image(trinket_icon_url)

        def build_notification_image():
            width, height = img.size
            information_row = 50  # hard coded bcs of knowing code of MatchToSend
            font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 34)
            draw = ImageDraw.Draw(img)

            # Item Icons
            items_row = information_row
            for count, item_image in enumerate(item_icon_images):
                left = count * items_row
                item_image = item_image.resize((items_row, items_row))
                img.paste(
                    im=item_image,
                    box=(left, height - information_row - item_image.height),
                )

            # Trinket Icon
            trinket_image = trinket_icon_img.resize((items_row, items_row))
            img.paste(
                im=trinket_image,
                box=(width - trinket_image.width, height - information_row - trinket_image.height),
            )

            # Skill Build
            # I got these images by downloading .png from
            # https://commons.wikimedia.org/wiki/Category:Emoji_One_BW
            # and using Paint Bucket Tool to give it proper colours
            # plus resized to 50x50 afterwards
            skill_slot_mapping = {
                1: "assets/images/local/Q.png",
                2: "assets/images/local/W.png",
                3: "assets/images/local/E.png",
                4: "assets/images/local/R.png",
            }
            skill_order_row = 40
            skill_slot_images = {
                skill_slot: Image.open(path).resize((skill_order_row, skill_order_row))
                for skill_slot, path in skill_slot_mapping.items()
            }

            for count, skill_slot in enumerate(reversed(self.skill_build)):
                skill_slot_image = skill_slot_images[skill_slot]
                img.paste(
                    im=skill_slot_image,
                    box=(
                        count * skill_slot_image.width,
                        height - information_row - items_row - skill_slot_image.height,
                    ),
                )

            # KDA Text
            kda_text_w, kda_text_h = self.bot.transposer.get_text_wh(self.kda, font)
            draw.text(
                (0, height - information_row - items_row - skill_order_row - kda_text_h),
                self.kda,
                font=font,
                align="right",
            )

            # Outcome Text
            outcome_text_w, outcome_text_h = self.bot.transposer.get_text_wh(self.outcome, font)
            colour_dict = {
                "Win": str(const.MaterialPalette.green(shade=800)),
                "Loss": str(const.MaterialPalette.red(shade=900)),
                "No Scored": (255, 255, 255),
            }
            draw.text(
                xy=(0, height - information_row - items_row - skill_order_row - kda_text_h - outcome_text_h - 5),
                text=self.outcome,
                font=font,
                align="center",
                fill=colour_dict[self.outcome],
            )

            return img

        return await asyncio.to_thread(build_notification_image)


if TYPE_CHECKING:
    from utils import AluCog


async def beta_test_edit_notification_image(self: AluCog):
    """Testing function for `edit_notification_image` from LoLFPCMatchToEdit class

    Import this into `beta_task` for easy testing of how new elements alignment.
    """
    # BETA TESTING USAGE
    # from .fpc_notifications.lol._models import beta_test_edit_notification_image
    # await beta_test_edit_notification_image(self)

    from extensions.fpc_notifications.lol._models import LoLFPCMatchToEdit

    await self.bot.initialize_league_pulsefire_clients()
    self.bot.initialize_league_cache()

    match_id = "NA1_4899995798"
    continent = "AMERICAS"
    match = await self.bot.riot_api_client.get_lol_match_v5_match(id=match_id, region=continent)
    timeline = await self.bot.riot_api_client.get_lol_match_v5_match_timeline(id=match_id, region=continent)

    post_match_player = LoLFPCMatchToEdit(
        self.bot,
        participant=match["info"]["participants"][0],
        timeline=timeline,
    )

    new_image = await post_match_player.edit_notification_image(
        const.PICTURE.PLACEHOLDER640X360, discord.Colour.purple()
    )
    new_image.show()
