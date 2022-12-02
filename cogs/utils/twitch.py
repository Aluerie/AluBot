from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext.commands import BadArgument
from twitchAPI import Twitch

from .format import gettimefromhms, display_hmstime

if TYPE_CHECKING:
    from asyncpg import Pool


async def get_lol_streams(pool: Pool, twitch: Twitch):
    async def get_all_fav_ids(column_name: str):
        query = f'SELECT DISTINCT(unnest({column_name})) FROM guilds'
        rows = await pool.fetch(query)
        return [row.unnest for row in rows]

    fav_stream_ids = await get_all_fav_ids('lolfeed_stream_ids')

    fav_stream_ids = [str(x) for x in list(set(fav_stream_ids))]
    data = twitch.get_streams(user_id=fav_stream_ids, first=100)['data']
    return [int(item['user_id']) for item in data]


class MyTwitchClient(Twitch):
    """My Twitch Client with extra functionality"""
    def __init__(self, client_id: str, client_secret):
        super().__init__(client_id, client_secret)

    def twitch_id_by_name(
            self,
            user_login: str
    ) -> int:
        data = self.get_users(logins=[user_login])['data']
        if data:
            return int(data[0]['id'])
        else:
            raise BadArgument(f'Error checking stream `{user_login}`.\n User either does not exist or is banned.')

    def name_by_twitch_id(self, user_id: int):
        data = self.get_users(user_ids=[str(user_id)])['data']
        return data[0]['display_name']

    def twitch_id_and_display_name_by_login(
            self,
            user_login: str
    ) -> (int, str):
        data = self.get_users(logins=[user_login])['data']
        if data:
            return int(data[0]['id']), data[0]['display_name']
        else:
            raise BadArgument(f'Error checking stream `{user_login}`.\n User either does not exist or is banned.')


class TwitchStream:
    def __init__(
            self,
            twitch_id: int,
            twitch: Twitch
    ):
        self.id = str(twitch_id)
        self.twitch = twitch

        def user_data(user_id: str):
            data = twitch.get_users(user_ids=[user_id])['data']
            return data[0] if data else None

        offline_data = user_data(self.id)

        def stream_data(user_id: str):
            data = twitch.get_streams(user_id=[user_id])['data']
            return data[0] if data else None

        online_data = stream_data(self.id)

        self.display_name = offline_data['display_name']
        self.name = offline_data['login']
        self.url = f'https://www.twitch.tv/{self.display_name}'
        self.logo_url = offline_data['profile_image_url']

        if online_data is not None:  # stream is online
            self.online = True
            self.game = online_data['game_name']
            self.title = online_data['title']
            self.preview_url = online_data['thumbnail_url'].replace('{width}', '640').replace('{height}', '360')
        else:
            self.online = False
            self.game = 'Offline'
            self.title = 'Offline'
            if (name_to_cut := offline_data['offline_image_url']) == '':
                self.preview_url = f'https://static-cdn.jtvnw.net/previews-ttv/live_user_{self.name}-640x360.jpg'
            else:
                self.preview_url = \
                    f'{"-".join(name_to_cut.split("-")[:-1])}-640x360.{name_to_cut.split(".")[-1]}'

    def last_vod_link(self, epoch_time_ago: int = 0, md: bool = True) -> str:
        try:
            last_vod = self.twitch.get_videos(user_id=self.id)['data'][0]
            duration_time = gettimefromhms(last_vod['duration'])
            vod_url = f'{last_vod["url"]}?t={display_hmstime(duration_time - epoch_time_ago)}'
            return f'/[TwVOD]({vod_url})' if md else vod_url
        except IndexError:
            return ''


if __name__ == '__main__':
    from twitchAPI import Twitch
    from config import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET

    twitch = MyTwitchClient(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
    twitch.authenticate_app([])

    tw_id = twitch.twitch_id_by_name('timado')
    re = TwitchStream(tw_id, twitch)
    print(re.preview_url)
