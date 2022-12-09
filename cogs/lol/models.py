"""
The MIT License (MIT)

"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import TYPE_CHECKING, List

from PIL import Image, ImageDraw, ImageFont
from discord import Embed
from pyot.utils.lol import champion
from pyot.utils.functools import async_property

from .const import platform_to_region
from .utils import get_role_mini_list, icon_url_by_champ_id
from ..utils.format import display_relativehmstime
from ..utils.imgtools import get_text_wh

from ..utils.twitch import TwitchStream
from ..utils.var import Clr, MP

if TYPE_CHECKING:
    from pyot.models.lol import Spell, Rune
    from pyot.models.lol.match import MatchParticipantData
    from ..utils.bot import AluBot

log = logging.getLogger(__name__)


class Match:
    def __init__(
            self,
            match_id: int,
            platform: str,
            acc_name: str
    ):
        self.match_id = match_id
        self.platform = platform
        self.acc_name = acc_name

        self.stripped_acc_name = self.acc_name.replace(" ", "")

    @property
    def opgg(self) -> str:  # todo: rework these links into actual match links
        """op.gg link for the match"""
        region = platform_to_region(self.platform)
        return f'https://{region}.op.gg/summoners/{region}/{self.stripped_acc_name}'

    @property
    def ugg(self) -> str:
        """u.gg link for the match"""
        return f'https://u.gg/lol/profile/{self.platform}/{self.stripped_acc_name}'

    @property
    def links(self) -> str:
        """all links at once"""
        return f'/[Opgg]({self.opgg})/[Ugg]({self.ugg})'

    # todo: delete this
    # def get_str_match_id(platform: str, match_id: int) -> str:
    #    return f'{platform.upper()}_{match_id}'


class ActiveMatch(Match):

    def __init__(
            self,
            *,
            match_id: int,
            platform: str,
            acc_name: str,
            start_time: int,
            champ_id: int,
            all_champ_ids: List[int],
            twitch_id: int,
            spells: List[Spell],
            runes: List[Rune]
    ):
        super().__init__(match_id, platform, acc_name)
        self.start_time = start_time
        self.champ_id = champ_id
        self.all_champ_ids = all_champ_ids
        self.twitch_id = twitch_id
        self.spells = spells
        self.runes = runes

    @property
    def long_ago(self):
        if self.start_time:
            return int(datetime.now(timezone.utc).timestamp() - self.start_time)
        else:
            return self.start_time

    @async_property
    async def roles_arr(self):
        return await get_role_mini_list(self.all_champ_ids)

    @async_property
    async def champ_name(self):
        return await champion.key_by_id(self.champ_id)

    @async_property
    async def champ_icon_url(self):
        return await icon_url_by_champ_id(self.champ_id)

    def twitch_stream(self, bot: AluBot) -> TwitchStream:
        return TwitchStream(self.twitch_id, bot.twitch)

    async def better_thumbnail(
            self,
            stream_preview_url: str,
            display_name: str,
            bot: AluBot
    ) -> Image:
        img = await bot.url_to_img(stream_preview_url)
        width, height = img.size
        last_row_h = 50
        last_row_y = height - last_row_h
        rectangle = Image.new("RGB", (width, 100), str(Clr.rspbrry))
        ImageDraw.Draw(rectangle)
        img.paste(rectangle)
        img.paste(rectangle, (0, last_row_y))

        champ_img_urls = [await icon_url_by_champ_id(champ_id) for champ_id in await self.roles_arr]
        champ_imgs = await bot.url_to_img(champ_img_urls)
        for count, champ_img in enumerate(champ_imgs):
            champ_img = champ_img.resize((62, 62))
            extra_space = 0 if count < 5 else 20
            img.paste(champ_img, (count * 62 + extra_space, 0))

        font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 33)
        draw = ImageDraw.Draw(img)
        text = f'{display_name} - {await self.champ_name}'
        w2, h2 = get_text_wh(text, font)
        draw.text(((width - w2) / 2, 65), text, font=font, align="center")

        rune_img_urls = [(await r.get()).icon_abspath for r in self.runes]
        rune_imgs = await bot.url_to_img(rune_img_urls)
        left = 0
        for count, rune_img in enumerate(rune_imgs):
            if count < 6:
                rune_img = rune_img.resize((last_row_h, last_row_h))
            img.paste(rune_img, (left, height - rune_img.height), rune_img)
            left += rune_img.height

        spell_img_urls = [(await s.get()).icon_abspath for s in self.spells]
        spell_imgs = await bot.url_to_img(spell_img_urls)
        left = width - 2 * last_row_h
        for count, spell_img in enumerate(spell_imgs):
            spell_img = spell_img.resize((last_row_h, last_row_h))
            img.paste(spell_img, (left + count * spell_img.width, height - spell_img.height))

        return img

    async def notif_embed_and_file(
            self,
            bot: AluBot
    ):
        twitch_stream = self.twitch_stream(bot)

        image_name = \
            f'{twitch_stream.display_name.replace("_", "")}-is-playing-' \
            f'{(await self.champ_name).replace(" ", "")}.png'
        img_file = bot.img_to_file(
            await self.better_thumbnail(twitch_stream.preview_url, twitch_stream.display_name, bot),
            filename=image_name
        )

        em = Embed(
            color=Clr.rspbrry,
            url=twitch_stream.url,
            description=
            f'Match `{self.match_id}` started {display_relativehmstime(self.long_ago)}\n'
            f'{twitch_stream.last_vod_link(epoch_time_ago=self.long_ago)}{self.links}'
        ).set_image(
            url=f'attachment://{image_name}'
        ).set_thumbnail(
            url=await self.champ_icon_url
        ).set_author(
            name=f'{twitch_stream.display_name} - {await self.champ_name}',
            url=twitch_stream.url,
            icon_url=twitch_stream.logo_url
        )
        return em, img_file


class PostMatchPlayerData:

    def __init__(
            self,
            player_data: MatchParticipantData
    ):
        self.player_id = player_data.summoner_id
        self.kda = f'{player_data.kills}/{player_data.deaths}/{player_data.assists}'
        self.outcome = "Win" if player_data.win else "Loss"
        self.items = player_data.items

    async def edit_the_image(self, img_url: str, bot: AluBot):

        img = await bot.url_to_img(img_url)
        width, height = img.size
        last_row_h = 50
        last_row_y = height - last_row_h
        font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 33)

        draw = ImageDraw.Draw(img)
        w3, h3 = get_text_wh(self.kda, font)
        draw.text(
            (0, height - last_row_h - h3),
            self.kda,
            font=font,
            align="right"
        )
        w2, h2 = get_text_wh(self.outcome, font)
        colour_dict = {
            'Win': str(MP.green(shade=800)),
            'Loss': str(MP.red(shade=900)),
            'No Scored': (255, 255, 255)
        }
        draw.text(
            (0, height - last_row_h - h3 - h2 - 5),
            self.outcome,
            font=font,
            align="center",
            fill=colour_dict[self.outcome]
        )

        item_img_urls = [(await i.get()).icon_abspath for i in self.items if i.id]
        item_imgs = await bot.url_to_img(item_img_urls, return_list=True)
        left = width - len(item_imgs) * last_row_h
        for count, item_img in enumerate(item_imgs):
            item_img = item_img.resize((last_row_h, last_row_h))
            img.paste(item_img, (left + count * item_img.width, height - last_row_h - item_img.height))
        return img
