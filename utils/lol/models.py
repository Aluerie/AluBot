from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import TYPE_CHECKING, List

import discord
from PIL import Image, ImageDraw, ImageFont
from pyot.utils.lol import champion
from pyot.utils.functools import async_property

from .const import LiteralPlatform, platform_to_server
from .utils import get_role_mini_list, icon_url_by_champ_id
from utils.formats import human_timedelta
from utils.var import Clr, MP

if TYPE_CHECKING:
    from pyot.models.lol import Spell, Rune
    from pyot.models.lol.match import MatchParticipantData
    from utils.bot import AluBot

__all__ = ('Account', 'Match', 'LiveMatch', 'PostMatchPlayer')


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Account:
    def __init__(self, platform: LiteralPlatform, account_name: str):
        self.platform: LiteralPlatform = platform
        self.account_name = account_name

        self._stripped_acc_name = self.account_name.replace(" ", "")

    @property
    def opgg(self) -> str:
        """op.gg link for the match"""
        server = platform_to_server(self.platform)
        return f'https://{server}.op.gg/summoners/{server}/{self._stripped_acc_name}'

    @property
    def ugg(self) -> str:
        """u.gg link for the match"""
        return f'https://u.gg/lol/profile/{self.platform}/{self._stripped_acc_name}'

    @property
    def links(self) -> str:
        """all links at once"""
        return f'/[Opgg]({self.opgg})/[Ugg]({self.ugg})'


class Match(Account):
    def __init__(self, match_id: int, platform: LiteralPlatform, account_name: str):
        super().__init__(platform, account_name)
        self.match_id: int = match_id


class LiveMatch(Match):
    def __init__(
        self,
        *,
        match_id: int,
        platform: LiteralPlatform,
        account_name: str,
        start_time: int,
        champ_id: int,
        all_champ_ids: List[int],
        twitch_id: int,
        spells: List[Spell],
        runes: List[Rune],
        channel_ids: List[int],
        account_id: str,
    ):
        super().__init__(match_id, platform, account_name)
        self.start_time = start_time
        self.champ_id = champ_id
        self.all_champ_ids = all_champ_ids
        self.twitch_id = twitch_id
        self.spells = spells
        self.runes = runes
        self.channel_ids = channel_ids
        self.account_id = account_id

    @property
    def long_ago(self):
        if self.start_time:
            return int(datetime.now(timezone.utc).timestamp() - self.start_time)
        else:
            return self.start_time

    @async_property
    async def roles_arr(self):
        log.debug('LF | gathering the roles')
        res = await get_role_mini_list(self.all_champ_ids)
        log.debug('LF | finished gathering the roles')
        return res

    @async_property
    async def champ_icon_url(self):
        return await icon_url_by_champ_id(self.champ_id)

    async def better_thumbnail(self, stream_preview_url: str, display_name: str, bot: AluBot) -> Image.Image:
        log.debug('I m here #1')
        img = await bot.imgtools.url_to_img(stream_preview_url)
        width, height = img.size
        last_row_h = 50
        last_row_y = height - last_row_h
        rectangle = Image.new("RGB", (width, 100), str(Clr.rspbrry))
        ImageDraw.Draw(rectangle)
        img.paste(rectangle)
        img.paste(rectangle, (0, last_row_y))
        log.debug('I m here #2')
        champ_img_urls = [await icon_url_by_champ_id(champ_id) for champ_id in await self.roles_arr]
        champ_imgs = await bot.imgtools.url_to_img(champ_img_urls)
        for count, champ_img in enumerate(champ_imgs):
            champ_img = champ_img.resize((62, 62))
            extra_space = 0 if count < 5 else 20
            img.paste(champ_img, (count * 62 + extra_space, 0))
        log.debug('I m here #3')
        font = ImageFont.truetype('./assets/fonts/Inter-Black-slnt=0.ttf', 33)
        draw = ImageDraw.Draw(img)
        text = f'{display_name} - {await champion.name_by_id(self.champ_id)}'
        w2, h2 = bot.imgtools.get_text_wh(text, font)
        draw.text(((width - w2) / 2, 65), text, font=font, align="center")
        log.debug('I m here #4')
        rune_img_urls = [(await r.get()).icon_abspath for r in self.runes]
        rune_imgs = await bot.imgtools.url_to_img(rune_img_urls)
        left = 0
        for count, rune_img in enumerate(rune_imgs):
            if count < 6:
                rune_img = rune_img.resize((last_row_h, last_row_h))
            img.paste(rune_img, (left, height - rune_img.height), rune_img)
            left += rune_img.height
        log.debug('I m here #5')
        spell_img_urls = [(await s.get()).icon_abspath for s in self.spells]
        spell_imgs = await bot.imgtools.url_to_img(spell_img_urls)
        left = width - 2 * last_row_h
        for count, spell_img in enumerate(spell_imgs):
            spell_img = spell_img.resize((last_row_h, last_row_h))
            img.paste(spell_img, (left + count * spell_img.width, height - spell_img.height))
        log.debug('I m here #6')
        return img

    async def notif_embed_and_file(self, bot: AluBot) -> (discord.Embed, discord.File):
        ts = await bot.twitch.get_twitch_stream(self.twitch_id)
        img_file = bot.imgtools.img_to_file(
            await self.better_thumbnail(ts.preview_url, ts.display_name, bot),
            filename=f'{ts.display_name.replace("_", "")}-is-playing-{await champion.key_by_id(self.champ_id)}.png',
        )
        log.debug('LF | made a better thumbnail')
        e = discord.Embed(color=Clr.rspbrry, url=ts.url)
        e.description = (
            f'Match `{self.match_id}` started {human_timedelta(self.long_ago, strip=True)}\n'
            f'{await bot.twitch.last_vod_link(ts.twitch_id, seconds_ago=self.long_ago)}{self.links}'
        )
        e.set_image(url=f'attachment://{img_file.filename}')
        e.set_thumbnail(url=await self.champ_icon_url)
        e.set_author(
            name=f'{ts.display_name} - {await champion.name_by_id(self.champ_id)}', url=ts.url, icon_url=ts.logo_url
        )
        return e, img_file


class PostMatchPlayer:
    def __init__(self, *, player_data: MatchParticipantData, channel_id: int, message_id: int):
        self.channel_id = channel_id
        self.message_id = message_id

        self.player_id = player_data.summoner_id
        self.kda = f'{player_data.kills}/{player_data.deaths}/{player_data.assists}'
        self.outcome = "Win" if player_data.win else "Loss"
        self.items = player_data.items

    async def edit_the_image(self, img_url: str, bot: AluBot):
        img = await bot.imgtools.url_to_img(img_url)
        width, height = img.size
        last_row_h = 50
        _last_row_y = height - last_row_h
        font = ImageFont.truetype('./assets/fonts/Inter-Black-slnt=0.ttf', 33)

        draw = ImageDraw.Draw(img)
        w3, h3 = bot.imgtools.get_text_wh(self.kda, font)
        draw.text((0, height - last_row_h - h3), self.kda, font=font, align="right")
        w2, h2 = bot.imgtools.get_text_wh(self.outcome, font)
        colour_dict = {'Win': str(MP.green(shade=800)), 'Loss': str(MP.red(shade=900)), 'No Scored': (255, 255, 255)}
        draw.text(
            (0, height - last_row_h - h3 - h2 - 5),
            self.outcome,
            font=font,
            align="center",
            fill=colour_dict[self.outcome],
        )

        item_img_urls = [(await i.get()).icon_abspath for i in self.items if i.id]
        item_imgs = await bot.imgtools.url_to_img(item_img_urls, return_list=True)
        left = width - len(item_imgs) * last_row_h
        for count, item_img in enumerate(item_imgs):
            item_img = item_img.resize((last_row_h, last_row_h))
            img.paste(item_img, (left + count * item_img.width, height - last_row_h - item_img.height))
        return img

    async def edit_the_embed(self, bot: AluBot):
        ch = bot.get_channel(self.channel_id)
        if ch is None:
            return  # wrong bot, I guess

        try:
            msg = await ch.fetch_message(self.message_id)
        except discord.NotFound:
            return

        e = msg.embeds[0]
        img_file = bot.imgtools.img_to_file(await self.edit_the_image(e.image.url, bot), filename='edited.png')
        e.set_image(url=f'attachment://{img_file.filename}')
        try:
            await msg.edit(embed=e, attachments=[img_file])
        except discord.Forbidden:
            return
