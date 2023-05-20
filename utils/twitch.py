from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, List, Optional, Tuple

import twitchio
from discord.ext.commands import BadArgument

from utils.formats import human_timedelta
from utils.lol.const import LOL_GAME_CATEGORY_TWITCH_ID

if TYPE_CHECKING:
    from asyncpg import Pool

log = logging.getLogger(__name__)


class TwitchClient(twitchio.Client):
    def __init__(self, token: str):
        super().__init__(token)

    async def twitch_id_by_name(self, user_name: str) -> int:
        """Gets twitch_id by user_login"""
        user: Optional[twitchio.User] = next(iter(await self.fetch_users(names=[user_name])), None)
        if user:
            return user.id
        else:
            raise BadArgument(f'Error checking stream `{user_name}`.\n User either does not exist or is banned.')

    async def name_by_twitch_id(self, user_id: int) -> str:
        """Gets display_name by twitch_id"""
        user: Optional[twitchio.User] = next(iter(await self.fetch_users(ids=[user_id])), None)
        if user:
            return user.display_name
        else:
            raise BadArgument(f'Error checking stream `{user_id}`.\n User either does not exist or is banned.')

    async def fpc_data_by_login(self, user_login: str) -> Tuple[int, str, str]:
        """Gets tuple (twitch_id, display_name) by user_login from one call to twitch client"""
        user: Optional[twitchio.User] = next(iter(await self.fetch_users(names=[user_login])), None)
        if user:
            return user.id, user.display_name, user.profile_image
        else:
            raise BadArgument(f'Error checking stream `{user_login}`.\n User either does not exist or is banned.')

    async def last_vod_link(self, user_id: int, seconds_ago: int = 0, md: bool = True) -> str:
        """Get last vod link for user with `user_id` with timestamp as well"""
        try:
            video: twitchio.Video = next(
                iter(await self.fetch_videos(user_id=user_id, period='day')), None  # type: ignore # ???
            )

            def get_time_from_hms(hms_time: str):
                """Convert time after `?t=` in vod link into amount of seconds

                03h51m08s -> 3 * 3600 + 51 * 60 + 8 = 13868
                """

                def regex_time(letter: str) -> int:
                    """h -> 3, m -> 51, s -> 8 for above example"""
                    pattern = r'\d+(?={})'.format(letter)
                    units = re.search(pattern, hms_time)
                    return int(units.group(0)) if units else 0

                timeunit_dict = {'h': 3600, 'm': 60, 's': 1}
                return sum([v * regex_time(letter) for letter, v in timeunit_dict.items()])

            duration = get_time_from_hms(video.duration)
            vod_url = f'{video.url}?t={human_timedelta(duration - seconds_ago, strip=True, suffix=False)}'
            return f'/[TwVOD]({vod_url})' if md else vod_url
        except IndexError:
            return ''

    async def get_live_lol_player_ids(self, pool: Pool) -> List[int]:
        """Get twitch ids for live League of Legends streams"""
        query = f"""SELECT twitch_id, name_lower
                    FROM lol_players
                    WHERE name_lower=ANY(
                        SELECT DISTINCT player_name FROM lol_favourite_players
                    )
                """
        twitch_id_to_fav_id_dict = {r.twitch_id: r.name_lower for r in await pool.fetch(query)}
        if not twitch_id_to_fav_id_dict:
            # otherwise fetch_streams fetches top100 streams and we dont want that.
            return []
        live_twitch_ids = [
            i.user.id
            for i in await self.fetch_streams(user_ids=list(twitch_id_to_fav_id_dict.keys()))
            if i.game_id == LOL_GAME_CATEGORY_TWITCH_ID
        ]
        return [twitch_id_to_fav_id_dict[i] for i in live_twitch_ids]

    async def get_twitch_stream(self, twitch_id: int) -> TwitchStream:
        user = next(iter(await self.fetch_users(ids=[twitch_id])))
        stream = next(iter(await self.fetch_streams(user_ids=[twitch_id])), None)  # None if offline
        return TwitchStream(twitch_id, user, stream)


class TwitchStream:
    __slots__ = ('twitch_id', 'display_name', 'name', 'game', 'url', 'logo_url', 'online', 'title', 'preview_url')

    if TYPE_CHECKING:
        display_name: str
        name: str
        game: str
        url: str
        logo_url: str
        online: bool
        title: str
        preview_url: str

    def __init__(self, twitch_id: int, user: twitchio.User, stream: Optional[twitchio.Stream]):
        self.twitch_id = twitch_id
        self._update(user, stream)

    def __repr__(self):
        return f"<Stream id={self.twitch_id} name={self.name} online={self.online} title={self.title}>"

    def _update(self, user: twitchio.User, stream: Optional[twitchio.Stream]):
        self.display_name = user.display_name
        self.name = user.name
        self.url = f'https://www.twitch.tv/{self.display_name}'
        self.logo_url = user.profile_image

        if stream:
            self.online = True
            self.game = stream.game_name
            self.title = stream.title
            self.preview_url = stream.thumbnail_url.replace('{width}', '640').replace('{height}', '360')
        else:
            self.online = False
            self.game = 'Offline'
            self.title = 'Offline'
            if n := user.offline_image:
                self.preview_url = f'{"-".join(n.split("-")[:-1])}-640x360.{n.split(".")[-1]}'
            else:
                self.preview_url = f'https://static-cdn.jtvnw.net/previews-ttv/live_user_{self.name}-640x360.jpg'


async def main():
    from config import TWITCH_TOKEN

    tc = TwitchClient(token=TWITCH_TOKEN)
    await tc.connect()
    tw_id = await tc.twitch_id_by_name('gorgc')
    print(await tc.get_twitch_stream(tw_id))

    await tc.close()


if __name__ == '__main__':
    import asyncio

    logging.basicConfig()
    log.setLevel(logging.DEBUG)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    # loop.close()
