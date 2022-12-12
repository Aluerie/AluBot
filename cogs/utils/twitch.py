from __future__ import annotations

from typing import TYPE_CHECKING, List

from discord.ext.commands import BadArgument

from twitchAPI.twitch import Twitch
from twitchAPI.helper import first

from .format import gettimefromhms, display_hmstime

if TYPE_CHECKING:
    from asyncpg import Pool
    from twitchAPI.object import TwitchUser, Stream


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

    async def last_vod_link(
            self,
            user_id: int,
            epoch_time_ago: int = 0,
            md: bool = True
    ) -> str:
        """Get last vod link for user with `user_id` with timestamp as well"""
        try:
            last_vod = await first(self.get_videos(user_id=str(user_id)))
            duration_time = gettimefromhms(last_vod.duration)
            vod_url = f'{last_vod.url}?t={display_hmstime(duration_time - epoch_time_ago)}'
            return f'/[TwVOD]({vod_url})' if md else vod_url
        except IndexError:
            return ''

    async def get_twitch_stream(self, twitch_id: int) -> TwitchStream:
        user = await first(self.get_users(user_ids=[str(twitch_id)]))
        stream = await first(self.get_streams(user_id=[str(twitch_id)]))
        return TwitchStream(twitch_id, user, stream)

    async def get_live_lol_player_ids(self, pool: Pool) -> List[int]:
        """Get twitch ids for live League of Legends streams"""
        query = f"""SELECT twitch_id, id
                    FROM lol_players
                    WHERE id=ANY(
                        SELECT DISTINCT(unnest(lolfeed_stream_ids)) FROM guilds
                    )
                """
        twitch_id_to_fav_id_dict = {r.twitch_id: r.id for r in await pool.fetch(query)}
        live_twitch_ids = [  # todo: if our list grows beyond 100 then we need more
            int(i.user_id)
            async for i in self.get_streams(user_id=list(twitch_id_to_fav_id_dict.keys()), first=100)
        ]
        return [twitch_id_to_fav_id_dict[i] for i in live_twitch_ids]


class TwitchStream:
    __slots__ = (
        'twitch_id',
        'display_name',
        'name',
        'game',
        'url',
        'logo_url',
        'online',
        'title',
        'preview_url'
    )

    if TYPE_CHECKING:
        display_name: str
        name: str
        game: str
        url: str
        logo_url: str
        online: bool
        title: str
        preview_url: str

    def __init__(
            self,
            twitch_id: int,
            user: TwitchUser,
            stream: Stream
    ):
        self.twitch_id = twitch_id
        self._update(user, stream)

    def _update(self, user: TwitchUser, stream: Stream):
        self.display_name = user.display_name
        self.name = user.login
        self.url = f'https://www.twitch.tv/{self.display_name}'
        self.logo_url = user.profile_image_url

        if stream:
            self.online = True
            self.game = stream.game_name
            self.title = stream.title
            self.preview_url = stream.thumbnail_url.replace('{width}', '640').replace('{height}', '360')
        else:
            self.online = False
            self.game = 'Offline'
            self.title = 'Offline'
            if n := user.offline_image_url:
                self.preview_url = f'{"-".join(n.split("-")[:-1])}-640x360.{n.split(".")[-1]}'
            else:
                self.preview_url = f'https://static-cdn.jtvnw.net/previews-ttv/live_user_{self.name}-640x360.jpg'


async def main():
    from config import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
    # main starts here
    tc = await MyTwitchClient(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)

    tw_id = await tc.twitch_id_by_name('gorgc')
    ts = await tc.get_twitch_stream(tw_id)
    print(ts.preview_url)

    await tc.close()


if __name__ == '__main__':
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    # loop.close()
