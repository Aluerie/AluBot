from discord import Embed, Streaming
from discord.ext import commands, tasks

from utils.var import *
from utils.format import display_hmstime, gettimefromhms
from utils.imgtools import url_to_file
from utils import database as db

import re
from twitchAPI import Twitch
from os import getenv
client_id = getenv("TWITCH_CLIENT_ID")
client_secret = getenv("TWITCH_CLIENT_SECRET")
twitch = Twitch(client_id, client_secret)
twitch.authenticate_app([])


def get_db_online_streams(dbclass, session=db.session):
    streamer_list = list(set([row.name for row in session.query(dbclass).filter_by(optin=1)]))
    data = twitch.get_streams(user_login=streamer_list, first=100)['data']
    return [item['user_login'] for item in data]


def get_offline_data(user):
    try:
        return twitch.get_users(logins=[user])['data'][0]
    except Exception as e:
        print(f"Error checking user: {e}, {user} is probably banned offline data")
        return False


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


my_twitch_name = 'Irene_Adler__'


class Twitch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mystream.start()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.bot or before.activities == after.activities or before.id == Uid.irene:
            return

        irene_server = self.bot.get_guild(Sid.irene)
        if after.guild != irene_server:
            return

        stream_rl = irene_server.get_role(Rid.live_stream)

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
            db.set_value(db.g, Sid.irene, irene_is_live=0)
            return
        elif db.get_value(db.g, Sid.irene, "irene_is_live"):
            return
        else:
            db.set_value(db.g, Sid.irene, irene_is_live=1)
        irene_server = self.bot.get_guild(Sid.irene)
        mention_role = irene_server.get_role(Rid.stream_lover)
        content = f'{mention_role.mention} and chat, our Highness **@{my_twitch_name}** just went live !'
        embed = Embed(colour=0x9146FF)
        embed.title = f'{tw.title}'
        embed.url = tw.url
        embed.description = f'Playing {tw.game}\n[Watch Stream]({tw.url})\n[VOD link]({tw.last_vod_link()})'
        embed.set_author(name=f'{my_twitch_name} just went live on Twitch!', icon_url=tw.logo_url, url=tw.url)
        embed.set_thumbnail(url=tw.logo_url)
        file = await url_to_file(self.bot.ses, tw.preview_url, filename='twtvpreview.png')
        embed.set_image(url=f'attachment://{file.filename}')
        embed.set_footer(text=f'Twitch.tv | With love, {irene_server.me.display_name}', icon_url=Img.twitchtv)
        await irene_server.get_channel(Cid.stream_notifs).send(content=content, embed=embed, file=file)

    @mystream.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class TwitchThanks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener(name='on_member_update')
    async def twitch_sub_role_logs(self, before, after):
        if after.guild.id != Sid.irene:
            return

        irene_server = self.bot.get_guild(Sid.irene)
        subs_role = irene_server.get_role(Rid.subs)

        embed = Embed(color=0x9678b6)
        embed.set_thumbnail(url=after.display_avatar.url)
        embed.set_footer(text=f'With love, {irene_server.me.display_name}')
        if subs_role in after.roles and subs_role not in before.roles:
            embed.title = "User got Irene's tw.tv sub"
            embed.description = f'{after.mention} just got {subs_role.mention} role in this server !'
            embed.add_field(name="{0}{0}{0}".format(Ems.peepoNiceDay), value="Thanks for the sub !")
        elif subs_role in before.roles and subs_role not in after.roles:
            embed.title = "User lost Irene's tw.tv sub"
            embed.description = f'{after.mention} lost {subs_role.mention} role in this server !'
            embed.add_field(name="{0}{0}{0}".format(Ems.FeelsRainMan), value="Sad news !")
        else:
            return
        await irene_server.get_channel(Cid.stream_notifs).send(embed=embed)


async def setup(bot):
    await bot.add_cog(Twitch(bot))
    await bot.add_cog(TwitchThanks(bot))
