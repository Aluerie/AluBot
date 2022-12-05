from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext.commands import BadArgument

from twitchAPI.twitch import Twitch
from twitchAPI.helper import first

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

    async def twitch_id_by_name(
            self,
            user_login: str
    ) -> int:
        """Gets twitch_id by user_login"""
        if user := await first(self.get_users(logins=[user_login])):
            return int(user.id)
        else:
            raise BadArgument(f'Error checking stream `{user_login}`.\n User either does not exist or is banned.')

    async def name_by_twitch_id(
            self,
            user_id: int
    ) -> str:
        """Gets display_name by twitch_id"""
        if user := await first(self.get_users(user_ids=[str(user_id)])):
            return user.display_name
        else:
            raise BadArgument(f'Error checking stream `{user_id}`.\n User either does not exist or is banned.')

    async def twitch_id_and_display_name_by_login(
            self,
            user_login: str
    ) -> (int, str):
        """Gets tuple (twitch_id, display_name) by user_login from one call to twitch client"""
        if user := await first(self.get_users(logins=[user_login])):
            return int(user.id), user.display_name
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


async def main():
    from config import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET

    twitch_client = MyTwitchClient(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
    await twitch_client.authenticate_app([])

    tw_id = await twitch_client.twitch_id_by_name('timado')
    re = TwitchStream(tw_id, twitch_client)
    print(re.preview_url)


if __name__ == '__main__':
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    #  loop.close()