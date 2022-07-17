from __future__ import annotations
from typing import TYPE_CHECKING, Union

from discord import Streaming, Intents, AllowedMentions
from discord.ext import commands

from utils.context import Context
from utils.mysteam import sd_login

from aiohttp import ClientSession
from steam.client import SteamClient
from dota2.client import Dota2Client
from github import Github
from twitchAPI import Twitch

from datetime import datetime, timezone

from os import getenv, environ, listdir
import logging

if TYPE_CHECKING:
    from discord import Interaction, Message

test_list = [  # for yen bot
    'birthday',
    'error',
]


def cog_check(cog_list):
    return any(item in test_list for item in cog_list)


YEN_JSK = True
YEN_GIT = cog_check(['dotacomments', 'copydota'])
YEN_STE = cog_check(['dotafeed', 'gamerstats'])
YEN_TWI = cog_check(['dotafeed', 'lolfeed', 'twitch'])


class AluBot(commands.Bot):
    def __init__(self, prefix, yen=False):
        super().__init__(
            command_prefix=prefix,
            activity=Streaming(
                name="$help",
                url='https://www.twitch.tv/aluerie'
            ),
            intents=Intents.all(),
            allowed_mentions=AllowedMentions(replied_user=False, everyone=False)  # .none()
        )
        self.on_ready_fired = False
        self.yen = yen

    async def setup_hook(self) -> None:
        self.__session = ClientSession()
        if self.yen:
            if YEN_STE:
                self.steam = SteamClient()
                self.dota = Dota2Client(self.steam)
                self.steam_lgn = getenv("STEAM_TEST_LGN")
                self.steam_psw = getenv("STEAM_TEST_PSW")
                sd_login(self.steam, self.dota, self.steam_lgn, self.steam_psw)
        else:
            self.steam = SteamClient()
            self.dota = Dota2Client(self.steam)
            self.steam_lgn = getenv("STEAM_LGN")
            self.steam_psw = getenv("STEAM_PSW")
            sd_login(self.steam, self.dota, self.steam_lgn, self.steam_psw)

        if not self.yen or YEN_GIT:
            self.github = Github(getenv('GIT_PERSONAL_TOKEN'))
            self.git_gameplay = self.github.get_repo("ValveSoftware/Dota2-Gameplay")
            self.git_tracker = self.github.get_repo("SteamDatabase/GameTracking-Dota2")

        if not self.yen or YEN_TWI:
            self.twitch = Twitch(getenv("TWITCH_CLIENT_ID"), getenv("TWITCH_CLIENT_SECRET"))
            self.twitch.authenticate_app([])

        environ["JISHAKU_NO_UNDERSCORE"] = "True"
        environ["JISHAKU_HIDE"] = "True" # need to be before loading jsk
        if self.yen and len(test_list):
            if YEN_JSK:
                await self.load_cog('jishaku')
            for item in test_list:
                await self.load_cog(f'cogs.{item}')
        else:
            await self.load_cog('jishaku')
            for filename in listdir('./cogs'):
                if filename.endswith('.py'):
                    await self.load_cog(f'cogs.{filename[:-3]}')

    async def load_cog(self, cog: str) -> None:
        try:
            await self.load_extension(cog)
        except Exception as e:
            await self.__session.close()
            raise e

    async def on_ready(self):
        if self.on_ready_fired:
            return
        else:
            self.on_ready_fired = True

        self.launch_time = datetime.now(timezone.utc)
        print(f'Logged in as {self.user}')

    @property
    def ses(self):
        if self.__session.closed:
            self.__session = ClientSession()
        return self.__session

    async def close(self) -> None:
        await super().close()
        await self.__session.close()

    async def get_context(self, origin: Union[Interaction, Message], /, *, cls=Context) -> Context:
        return await super().get_context(origin, cls=cls)


class LogHandler(logging.StreamHandler):

    def __init__(self, papertrail=False):
        logging.StreamHandler.__init__(self)
        if papertrail:  # Yennifer Bot
            fmt = '%(levelname)-5.5s| %(filename)-15s|%(lineno)-4d|%(asctime)s| %(message)s'
            fmt_date = "%H:%M:%S"  # '%Y-%m-%dT%T%Z'
            formatter = logging.Formatter(fmt, fmt_date)
            self.setFormatter(formatter)
        else:  # Violet Bot
            fmt = '%(filename)-15s|%(lineno)-4d| %(message)s'
            formatter = logging.Formatter(fmt)
            self.setFormatter(formatter)
            pass
