from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, Optional, override

import discord
from PIL import Image, ImageDraw, ImageFont

from utils import const, lol
from utils.formats import human_timedelta
from utils.lol.const import LiteralPlatform, platform_to_server

from .._fpc_utils.base_models import BasePostMatchPlayer

if TYPE_CHECKING:
    from bot import AluBot


__all__ = ("Account", "Match", "LoLNotificationMatch", "PostMatchPlayer")


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Account:
    def __init__(self, platform: LiteralPlatform, account_name: str):
        self.platform: LiteralPlatform = platform
        self.account_name = account_name

        self._stripped_acc_name = self.account_name.replace(" ", "")

    @property
    def opgg(self) -> str:  # todo: look how to do actual links to matches instead of accounts
        """op.gg link for the match"""
        server = platform_to_server(self.platform)
        return f"https://{server}.op.gg/summoners/{server}/{self._stripped_acc_name}"

    @property
    def ugg(self) -> str:
        """u.gg link for the match"""
        return f"https://u.gg/lol/profile/{self.platform}/{self._stripped_acc_name}"

    @property
    def links(self) -> str:
        """all links at once"""
        return f"/[Opgg]({self.opgg})/[Ugg]({self.ugg})"


class Match(Account):
    def __init__(self, match_id: int, platform: LiteralPlatform, account_name: str):
        super().__init__(platform, account_name)
        self.match_id: int = match_id


class LoLNotificationMatch(Match):
    def __init__(
        self,
        *,
        match_id: int,
        platform: LiteralPlatform,
        account_name: str,
        start_time: int,
        champion_id: int,
        all_champion_ids: list[int],
        twitch_id: int,
        summoner_spell_ids: tuple[int, int],
        rune_ids: list[int],
        channel_ids: list[int],
        summoner_id: str,
    ):
        super().__init__(match_id, platform, account_name)
        self.start_time: int = start_time
        self.champion_id: int = champion_id
        self.all_champion_ids: list[int] = all_champion_ids
        self.twitch_id: int = twitch_id
        self.summoner_spell_ids: tuple[int, int] = summoner_spell_ids
        self.rune_ids: list[int] = rune_ids
        self.channel_ids: list[int] = channel_ids
        self.summoner_id: str = summoner_id

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
        bot: AluBot,
    ) -> Image.Image:
        # prepare stuff for the following PIL procedures
        img = await bot.transposer.url_to_image(stream_preview_url)
        sorted_champion_ids = await lol.roles.sort_champions_by_roles(self.all_champion_ids)
        champion_icon_urls = [await lol.champion.icon_by_id(id) for id in sorted_champion_ids]
        champion_icon_images = [await bot.transposer.url_to_image(url) for url in champion_icon_urls]
        rune_icon_urls = [await lol.rune.icon_by_id(id) for id in self.rune_ids]
        rune_icon_images = [await bot.transposer.url_to_image(url) for url in rune_icon_urls]
        summoner_icon_urls = [await lol.summoner_spell.icon_by_id(id) for id in self.summoner_spell_ids]
        summoner_icon_images = [await bot.transposer.url_to_image(url) for url in summoner_icon_urls]

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
            w2, _h2 = bot.transposer.get_text_wh(text, font)
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

    async def get_embed_and_file(self, bot: AluBot) -> tuple[discord.Embed, discord.File]:
        stream = await bot.twitch.get_twitch_stream(self.twitch_id)
        champion_name = await lol.champion.name_by_id(self.champion_id)

        notification_image = await self.get_notification_image(
            stream.preview_url, stream.display_name, champion_name, bot
        )

        filename = f'{stream.display_name.replace("_", "")}-playing-{champion_name}.png'
        image_file = bot.transposer.image_to_file(notification_image, filename=filename)

        embed = discord.Embed(color=const.Colour.rspbrry(), url=stream.url)
        embed.description = (
            f"Match `{self.match_id}` started {human_timedelta(self.long_ago, strip=True)}\n"
            f"{await bot.twitch.last_vod_link(stream.twitch_id, seconds_ago=self.long_ago)}{self.links}"
        )
        embed.set_image(url=f"attachment://{image_file.filename}")
        embed.set_thumbnail(url=await lol.champion.icon_by_id(self.champion_id))
        embed.set_author(name=f"{stream.display_name} - {champion_name}", url=stream.url, icon_url=stream.logo_url)
        return embed, image_file


class PostMatchPlayer(BasePostMatchPlayer):
    def __init__(
        self,
        *,
        channel_id: int,
        message_id: int,
        summoner_id: str,
        kda: str,
        outcome: str,
        item_ids: list[int],
    ):
        super().__init__(channel_id=channel_id, message_id=message_id)
        self.summoner_id: str = summoner_id
        self.kda: str = kda
        self.outcome: str = outcome
        self.item_ids: list[int] = item_ids

    @override
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour, bot: AluBot) -> Image.Image:
        img = await bot.transposer.url_to_image(embed_image_url)
        item_icon_urls = [await lol.item.icon_by_id(item_id) for item_id in self.item_ids if item_id]
        item_icon_images = [await bot.transposer.url_to_image(url) for url in item_icon_urls]

        def build_notification_image():
            width, height = img.size
            information_row = 50
            font = ImageFont.truetype("./assets/fonts/Inter-Black-slnt=0.ttf", 33)
            draw = ImageDraw.Draw(img)

            # kda text
            kda_text_w, kda_text_h = bot.transposer.get_text_wh(self.kda, font)
            draw.text((0, height - information_row - kda_text_h), self.kda, font=font, align="right")

            # outcome text
            outcome_text_w, outcome_text_h = bot.transposer.get_text_wh(self.outcome, font)
            colour_dict = {
                "Win": str(const.MaterialPalette.green(shade=800)),
                "Loss": str(const.MaterialPalette.red(shade=900)),
                "No Scored": (255, 255, 255),
            }
            draw.text(
                xy=(0, height - information_row - kda_text_h - outcome_text_h - 5),
                text=self.outcome,
                font=font,
                align="center",
                fill=colour_dict[self.outcome],
            )

            # item icons
            left = width - len(item_icon_images) * information_row
            for count, item_image in enumerate(item_icon_images):
                item_image = item_image.resize((information_row, information_row))
                img.paste(item_image, (left + count * item_image.width, height - information_row - item_image.height))

            return img

        return await asyncio.to_thread(build_notification_image)
