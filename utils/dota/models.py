"""
The MIT License (MIT)

"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional, Literal

from PIL import Image, ImageOps, ImageDraw, ImageFont
from discord import Embed, NotFound, Forbidden

from pyot.utils.functools import async_property

from utils import database as db
from utils.dota import hero, item, ability
from utils.format import display_relativehmstime
from utils.imgtools import url_to_img, img_to_file
from utils.twitch import TwitchStream
from utils.var import Clr, MP, Img

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from discord import TextChannel

__all__ = (
    'Match',
    'ActiveMatch',
    'PlayerAfterMatch'
)

log = logging.getLogger('root')
log.setLevel(logging.INFO)


dota_player_colour_map = {
    0: "#3375FF", 1: "#66FFBF", 2: "#BF00BF", 3: "#F3F00B", 4: "#FF6B00",
    5: "#FE86C2", 6: "#A1B447", 7: "#65D9F7", 8: "#008321", 9: "#A46900"
}


class Match:
    def __init__(
            self,
            match_id: int
    ):
        self.match_id = match_id

    def dbuff(self, md: bool = True) -> str:
        """Dotabuff.com link for the match with `match_id`"""
        url = f'https://www.dotabuff.com/matches/{self.match_id}'
        return f'/[Dbuff]({url})' if md else url

    def odota(self, md: bool = True) -> str:
        """Opendota.com link for the match with `match_id`"""
        url = f'https://www.opendota.com/matches/{self.match_id}'
        return f'/[ODota]({url})' if md else url

    def stratz(self, md: bool = True) -> str:
        """Stratz.com link for `match_id`"""
        url = f'https://www.stratz.com/matches/{self.match_id}'
        return f'/[Stratz]({url})' if md else url

    def replay(self, matchtime: int = 0, md: bool = True) -> str:
        """replay link which opens dota 2 client"""
        url = f'dota2://matchid={self.match_id}&matchtime={matchtime}'
        return f'/[Replay]({url})' if md else url

    def links(self) -> str:
        """all three links at once"""
        return f'{self.dbuff()}{self.odota()}{self.stratz()}'  # {self.replay()}'


colour_twitch_status_dict = {
    'NoTwitch': MP.gray(),
    'Live': Clr.prpl,
    'Offline': Clr.twitch
}


class ActiveMatch(Match):
    def __init__(
            self,
            *,
            match_id: int,
            start_time: int,
            player_name: str,
            hero_id: int,
            hero_ids: List[int],
            server_steam_id: int,
            twitchtv_id: Optional[int] = None,
            channel_id: int,
    ):
        super().__init__(match_id)
        self.start_time = start_time
        self.player_name = player_name
        self.hero_id = hero_id
        self.hero_ids = hero_ids
        self.server_steam_id = server_steam_id
        self.twitchtv_id = twitchtv_id
        self.channel_id = channel_id

        if self.twitchtv_id is None:
            self.twtv = None
            self.img_url = 'https://i.imgur.com/kl0jDOu.png'  # lavender 640x360
            self.display_name = self.player_name
            self.url = ''
            self.logo_url = Img.dota2logo
            self.twitch_status = 'NoTwitch'
        else:
            self.twtv = TwitchStream(self.twitchtv_id)
            self.img_url = self.twtv.preview_url
            self.display_name = self.twtv.display_name
            self.logo_url = self.twtv.logo_url
            self.url = self.twtv.url
            if self.twtv.online:
                self.twitch_status = 'Live'
            else:
                self.twitch_status = 'Offline'
        self.colour = colour_twitch_status_dict[self.twitch_status]

    @property
    def long_ago(self) -> int:
        return int(datetime.now(timezone.utc).timestamp()) - self.start_time

    @property
    def vod_link(self):
        return '' if getattr(self.twtv, 'online', None) else self.twtv.last_vod_link(epoch_time_ago=self.long_ago)

    @async_property
    async def hero_name(self):
        return await hero.name_by_id(self.hero_id)

    async def better_thumbnail(
            self,
            session: ClientSession,
    ):
        img = await url_to_img(session, self.img_url)
        width, height = img.size
        rectangle = Image.new("RGB", (width, 70), str(self.colour))
        ImageDraw.Draw(rectangle)
        img.paste(rectangle)

        for count, hero_id in enumerate(self.hero_ids):
            hero_img = await url_to_img(session, await hero.iconurl_by_id(hero_id))
            # h_width, h_height = heroImg.size
            hero_img = hero_img.resize((62, 35))
            hero_img = ImageOps.expand(hero_img, border=(0, 3, 0, 0), fill=dota_player_colour_map.get(count))
            extra_space = 0 if count < 5 else 20
            img.paste(hero_img, (count * 62 + extra_space, 0))

        font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 33)
        draw = ImageDraw.Draw(img)
        text = f'{self.display_name} - {await self.hero_name}'
        w2, h2 = draw.textsize(text, font=font)
        draw.text(((width - w2) / 2, 35), text, font=font, align="center")

        draw = ImageDraw.Draw(img)
        w2, h2 = draw.textsize(text, font=font)
        draw.text((0, 35 + h2 + 10), self.twitch_status, font=font, align="center", fill=str(self.colour))
        return img

    async def notif_embed(
            self,
            session: ClientSession
    ):
        image_name = \
            f'{self.twitch_status}-' \
            f'{self.display_name.replace("_", "")}-' \
            f'{(await self.hero_name).replace(" ", "").replace(chr(39), "")}.png'  # chr39 is "'"
        img_file = img_to_file(await self.better_thumbnail(session), filename=image_name)

        em = Embed(
            colour=self.colour,
            url=self.url,
            description=
            f'`/match {self.match_id}` started {display_relativehmstime(self.long_ago)}\n'
            f'{self.vod_link}{self.links()}'
        ).set_image(
            url=f'attachment://{img_file.filename}'
        ).set_thumbnail(
            url=await hero.iconurl_by_id(self.hero_id)
        ).set_author(
            name=f'{self.display_name} - {await self.hero_name}',
            url=self.url,
            icon_url=self.logo_url
        ).set_footer(
            text=f'Console: watch_server {self.server_steam_id}'
        )
        return em, img_file

    async def send_the_embed(self, bot, db_ses):
        log.info("sending dota 2 embed")
        ch: TextChannel = bot.get_channel(self.channel_id)
        if ch is None:
            pass
        em, img_file = await self.notif_embed(bot.ses)
        em.title = f"{ch.guild.owner.name}'s fav hero + fav player spotted"
        msg = await ch.send(embed=em, file=img_file)
        db.add_row(
            db.em,
            msg.id,
            match_id=self.match_id,
            ch_id=ch.id,
            hero_id=self.hero_id,
            twitch_status=self.twitch_status
        )


class PlayerAfterMatch:

    def __init__(
            self,
            *,
            data: dict,
            channel_id: int,
            message_id: int,
            twitch_status: Literal['NoTwitch', 'Offline', 'Online'],
    ):
        self.channel_id = channel_id
        self.message_id = message_id
        self.twitch_status = twitch_status

        self.colour = colour_twitch_status_dict[self.twitch_status]

        self.match_id: int = data['match_id']
        self.hero_id: int = data['hero_id']
        self.outcome = "Win" if data['win'] else "Loss"
        self.ability_upgrades_arr = data['ability_upgrades_arr']
        self.items = [data[f'item_{i}'] for i in range(6)]
        self.kda = f'{data["kills"]}/{data["deaths"]}/{data["assists"]}'
        self.purchase_log = data['purchase_log']
        self.aghs_blessing = False
        self.aghs_shard = False
        permanent_buffs = data['permanent_buffs'] or []  # [] if it is None
        for pb in permanent_buffs:
            if pb['permanent_buff'] == 12:
                self.aghs_shard = True
            if pb['permanent_buff'] == 2:
                self.aghs_blessing = True

    def __repr__(self) -> str:
        pairs = ' '.join([f'{k}={v!r}' for k, v in self.__dict__.items()])
        return f'<{self.__class__.__name__} {pairs}>'

    async def edit_the_image(self, img_url, session):

        img = await url_to_img(session, img_url)

        width, height = img.size
        last_row_h = 50

        rectangle = Image.new("RGB", (width, last_row_h), str(self.colour))
        ImageDraw.Draw(rectangle)

        last_row_y = height - last_row_h
        img.paste(rectangle, (0, last_row_y))

        font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 26)

        draw = ImageDraw.Draw(img)
        w3, h3 = draw.textsize(self.kda, font=font)
        draw.text(
            (0, height - h3),
            self.kda,
            font=font,
            align="right"
        )

        draw = ImageDraw.Draw(img)
        w2, h2 = draw.textsize(self.outcome, font=font)
        colour_dict = {
            'Win': str(MP.green(shade=800)),
            'Loss': str(MP.red(shade=900)),
            'No Scored': (255, 255, 255)
        }
        draw.text(
            (0, height - h3 - h2),
            self.outcome,
            font=font,
            align="center",
            fill=colour_dict[self.outcome]
        )

        font_m = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 19)

        async def item_timing_text(item_id, x_left):
            for i in reversed(self.purchase_log):
                if item_id == await item.id_by_key(i['key']):
                    text = f"{math.ceil(i['time']/60)}m"
                    w7, h7 = draw.textsize(self.outcome, font=font_m)
                    draw.text(
                        (x_left, height-h7),
                        text,
                        font=font_m,
                        align="left"
                    )
                    return

        left_i = width - 69 * 6
        for count, itemId in enumerate(self.items):
            hero_img = await url_to_img(session, await item.iconurl_by_id(itemId))
            # h_width, h_height = heroImg.size # naturally in (88, 64)
            hero_img = hero_img.resize((69, 50))  # 69/50 - to match 88/64
            curr_left = left_i + count * hero_img.width
            img.paste(hero_img, (curr_left, height - hero_img.height))
            await item_timing_text(itemId, curr_left)

        ability_h = 37
        for count, abilityId in enumerate(self.ability_upgrades_arr):
            abil_img = await url_to_img(session, await ability.iconurl_by_id(abilityId))
            abil_img = abil_img.resize((ability_h, ability_h))
            img.paste(abil_img, (count * ability_h, last_row_y - abil_img.height))

        talent_strs = []
        for x in self.ability_upgrades_arr:
            if (dname := await ability.name_by_id(x)) is not None:
                talent_strs.append(dname)

        font = ImageFont.truetype('./media/Inter-Black-slnt=0.ttf', 12)
        for count, txt in enumerate(talent_strs):
            draw = ImageDraw.Draw(img)
            w4, h4 = draw.textsize(txt, font=font)
            draw.text(
                (width - w4, last_row_y - 30 * 2 - 22 * count),
                txt,
                font=font,
                align="right"
            )
        right = left_i
        if self.aghs_blessing:
            bless_img = await url_to_img(session, ability.lazy_aghs_bless_url)
            bless_img = bless_img.resize((48, 35))
            img.paste(bless_img, (right - bless_img.width, height - bless_img.height))
            await item_timing_text(271, right - bless_img.width)
            right -= bless_img.width
        if self.aghs_shard:
            shard_img = await url_to_img(session, ability.lazy_aghs_shard_url)
            shard_img = shard_img.resize((48, 35))
            img.paste(shard_img, (right - shard_img.width, height - shard_img.height))
            await item_timing_text(609, right - shard_img.width)

        #img.show()
        return img

    async def edit_the_embed(self, bot, db_ses):
        ch = bot.get_channel(self.channel_id)
        if ch is None:
            return  # wrong bot, I guess

        try:
            msg = await ch.fetch_message(self.message_id)
        except NotFound:
            return

        em = msg.embeds[0]
        image_name = 'edited.png'
        img_file = img_to_file(
            await self.edit_the_image(
                em.image.url,
                bot.ses
            ),
            filename=image_name
        )

        em.set_image(url=f'attachment://{image_name}')
        try:
            await msg.edit(embed=em, attachments=[img_file])
        except Forbidden:
            return

        db_ses.query(db.em).filter_by(id=self.message_id).delete()


if __name__ == '__main__':

    xcali = ActiveMatch(
        match_id=0,
        start_time=0,
        player_name='me',
        hero_id=3,
        hero_ids=[3, 4, 5],
        server_steam_id=9999,
        twitchtv_id=7777,
        channel_id=8888
    )
    print(xcali.__dict__)







