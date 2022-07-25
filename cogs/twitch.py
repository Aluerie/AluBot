from __future__ import annotations
from typing import TYPE_CHECKING
from discord import Embed, Streaming
from discord.ext import commands, tasks

from utils.var import *
from utils.format import display_hmstime, gettimefromhms
from utils.imgtools import url_to_file
from utils import database as db

import re
from twitchAPI import Twitch
from os import getenv

if TYPE_CHECKING:
    from discord import Member

client_id = getenv("TWITCH_CLIENT_ID")
client_secret = getenv("TWITCH_CLIENT_SECRET")
twitch = Twitch(client_id, client_secret)
twitch.authenticate_app([])


def get_lol_streams(session=db.session):
    fav_stream_ids = []
    for row in session.query(db.ga):
        fav_stream_ids += row.lolfeed_stream_ids
    fav_stream_ids = [str(x) for x in list(set(fav_stream_ids))]
    data = twitch.get_streams(user_id=fav_stream_ids, first=100)['data']
    return [item['user_id'] for item in data]


def get_dota_streams(session=db.session):
    fav_stream_ids = []
    for row in session.query(db.ga):
        fav_stream_ids += row.dotafeed_stream_ids
    fav_stream_ids = [str(x) for x in list(set(fav_stream_ids))]
    data = twitch.get_streams(user_id=fav_stream_ids, first=100)['data']
    return [item['user_id'] for item in data]


def get_offline_data(user):
    try:
        return twitch.get_users(logins=[user])['data'][0]
    except Exception as e:
        print(f"Error checking user: {e}, {user} is probably banned offline data")
        return False


def get_twtv_id(user: str):
    try:
        data = twitch.get_users(logins=[user])['data'][0]
        return data['id']
    except Exception as e:
        print(f"Error checking user: {e}, {user} is probably banned offline data")
        return None


def twitch_by_id(id_: int):
    try:
        data = twitch.get_users(user_ids=[str(id_)])['data'][0]
        return data['display_name']
    except Exception as e:
        print(f"Error checking user: {e}, {id_} is probably banned offline data")
        return None


def check_user(user):  # returns true if online, false if not
    try:
        data = twitch.get_streams(user_login=user)['data']
        return data[0] if data else None
    except Exception as e:
        print(f"Error checking user: {e}, {user} is probably banned")
        return None


class TwitchStream:
    def __init__(self, name):
        self.name = name
        offline_data = get_offline_data(name)
        self.logo_url = offline_data['profile_image_url']
        self.url = f'https://www.twitch.tv/{name}'
        if (json := check_user(name)) is not None:
            self.online = True
            self.game = json['game_name']
            self.preview_url = json['thumbnail_url'].replace('{width}', '640').replace('{height}', '360')
            self.title = json['title']
            self.id = json['user_id']
            self.display_name = json['user_name']
        else:
            self.online = False
            self.display_name = offline_data['display_name']
            self.game = 'Offline'
            if (name_to_cut := offline_data['offline_image_url']) == '':
                self.preview_url = f'https://static-cdn.jtvnw.net/previews-ttv/live_user_{name}-640x360.jpg'
            else:
                self.preview_url = f'{re.split("offline_image-", name_to_cut)[0]}offline_image-640x360.jpeg'
            self.title = 'Offline'
            self.id = offline_data['id']

    def last_vod_link(self, time_ago=0):
        try:
            last_vod = twitch.get_videos(user_id=self.id)['data'][0]
            duration_time = gettimefromhms(last_vod['duration'])
            return f'{last_vod["url"]}?t={display_hmstime(duration_time - time_ago)}'
        except IndexError:
            return None


my_twitch_name = 'Aluerie'


class Twitch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mystream.start()

    @commands.Cog.listener()
    async def on_presence_update(self, before: Member, after: Member):
        if before.bot or before.activities == after.activities or before.id == Uid.alu:
            return

        guild = self.bot.get_guild(Sid.alu)
        if after.guild != guild:
            return

        stream_rl = guild.get_role(Rid.live_stream)

        stream_after = None
        for item in after.activities:
            if isinstance(item, Streaming):
                stream_after = item

        if stream_rl not in after.roles and stream_after is not None:  # friend started the stream
            await after.add_roles(stream_rl)
        elif stream_rl in after.roles and stream_after is None:  # friend ended the stream
            await after.remove_roles(stream_rl)
        else:
            return

    @tasks.loop(minutes=2)
    async def mystream(self):
        tw = TwitchStream(my_twitch_name)
        if not tw.online:
            db.set_value(db.b, Sid.alu, irene_is_live=0)
            return
        elif db.get_value(db.b, Sid.alu, "irene_is_live"):
            return
        else:
            db.set_value(db.b, Sid.alu, irene_is_live=1)
        guild = self.bot.get_guild(Sid.alu)
        mention_role = guild.get_role(Rid.stream_lover)
        content = f'{mention_role.mention} and chat, our Highness **@{my_twitch_name}** just went live !'
        file = await url_to_file(self.bot.ses, tw.preview_url, filename='twtvpreview.png')
        em = Embed(
            colour=0x9146FF,
            title=f'{tw.title}',
            url=tw.url,
            description=
            f'Playing {tw.game}\n[Watch Stream]({tw.url})\n[VOD link]({tw.last_vod_link()})',
        ).set_author(
            name=f'{my_twitch_name} just went live on Twitch!',
            icon_url=tw.logo_url,
            url=tw.url
        ).set_footer(
            text=f'Twitch.tv | With love, {guild.me.display_name}',
            icon_url=Img.twitchtv
        ).set_thumbnail(
            url=tw.logo_url
        ).set_image(
            url=f'attachment://{file.filename}'
        )
        await guild.get_channel(Cid.stream_notifs).send(content=content, embed=em, file=file)

    @mystream.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class TwitchThanks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener(name='on_member_update')
    async def twitch_sub_role_logs(self, before, after):
        if after.guild.id != Sid.alu:
            return

        guild = self.bot.get_guild(Sid.alu)
        subs_role = guild.get_role(Rid.subs)

        em = Embed(color=0x9678b6)
        em.set_thumbnail(url=after.display_avatar.url)
        em.set_footer(text=f'With love, {guild.me.display_name}')
        if subs_role in after.roles and subs_role not in before.roles:
            em.title = "User got Aluerie's tw.tv sub"
            em.description = f'{after.mention} just got {subs_role.mention} role in this server !'
            em.add_field(name="{0}{0}{0}".format(Ems.peepoNiceDay), value="Thanks for the sub !")
        elif subs_role in before.roles and subs_role not in after.roles:
            em.title = "User lost Aluerie's tw.tv sub"
            em.description = f'{after.mention} lost {subs_role.mention} role in this server !'
            em.add_field(name="{0}{0}{0}".format(Ems.FeelsRainMan), value="Sad news !")
        else:
            return
        await guild.get_channel(Cid.stream_notifs).send(embed=em)


async def setup(bot):
    await bot.add_cog(Twitch(bot))
    await bot.add_cog(TwitchThanks(bot))
