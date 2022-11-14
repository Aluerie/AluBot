from __future__ import annotations

import logging
from datetime import datetime, timezone
from os import environ, listdir
from typing import TYPE_CHECKING, Union, Dict, Optional, Tuple, List, Sequence

from aiohttp import ClientSession
from discord import Streaming, Intents, AllowedMentions
from discord.ext import commands
from dota2.client import Dota2Client
from github import Github
from steam.client import SteamClient

from config import GIT_PERSONAL_TOKEN, STEAM_TEST_LGN, STEAM_TEST_PSW, STEAM_LGN, STEAM_PSW
from . import database as db
from . import imgtools
from .context import Context
from .var import Sid

#  from twitchAPI import Twitch

if TYPE_CHECKING:
    from discord import AppInfo, File, Interaction, Message, User
    from discord.app_commands import AppCommand
    from discord.abc import Snowflake

    from github import Repository

log = logging.getLogger('root')

try:
    from tlist import test_list
except ModuleNotFoundError:
    test_list = []


def cog_check(cog_list):
    if not len(test_list):
        return True
    else:
        return any(item in test_list for item in cog_list)


YEN_JSK = True
YEN_GIT = cog_check(['dotacomments', 'copydota'])
YEN_STE = cog_check(['dotafpfc', 'gamerstats', 'tools', 'rankedinfo'])


# YEN_TWITCH = cog_check(['dotafeed', 'lolfeed', 'twitch'])

async def alubot_get_pre(bot: AluBot, message: Message):
    if message.guild is None:
        prefix = '$'
    else:
        prefix = db.get_value(db.ga, message.guild.id, 'prefix')
    return commands.when_mentioned_or(prefix, "/")(bot, message)


class AluBot(commands.Bot):
    bot_app_info: AppInfo
    steam: SteamClient
    dota: Dota2Client
    github: Github
    git_gameplay: Repository
    git_tracker: Repository
    __session: ClientSession
    launch_time: datetime

    def __init__(self, yen=False):
        prefix = '~' if yen else alubot_get_pre
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
        self.app_commands: Dict[str, int] = {}

    async def setup_hook(self) -> None:
        self.__session = ClientSession()
        self.bot_app_info = await self.application_info()

        if not self.yen or YEN_STE:
            self.steam = SteamClient()
            self.dota = Dota2Client(self.steam)
            self.steam_dota_login()

        if not self.yen or YEN_GIT:
            self.github = Github(GIT_PERSONAL_TOKEN)
            self.git_gameplay = self.github.get_repo("ValveSoftware/Dota2-Gameplay")
            self.git_tracker = self.github.get_repo("SteamDatabase/GameTracking-Dota2")

        """
        if not self.yen or YEN_TWITCH:
            self.twitch = Twitch(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
            self.twitch.authenticate_app([])
        """

        if not self.yen or YEN_JSK:
            environ["JISHAKU_NO_UNDERSCORE"] = "True"
            environ["JISHAKU_HIDE"] = "True"  # need to be before loading jsk
            await self.load_cog('jishaku')

        if self.yen and len(test_list):
            extensions_list = [f'cogs.{name}' for name in test_list]
        else:
            extensions_list = [f'cogs.{filename[:-3]}' for filename in listdir('./cogs') if filename.endswith('.py')]

        for ext in extensions_list:
            await self.load_cog(ext)

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

    @property
    def owner(self) -> User:
        return self.bot_app_info.owner

    def steam_dota_login(self):
        if self.steam.connected is False:
            log.info(f"dota2info: client.connected {self.steam.connected}")
            if self.yen:
                steam_login = STEAM_TEST_LGN
                steam_password = STEAM_TEST_PSW
            else:
                steam_login = STEAM_LGN
                steam_password = STEAM_PSW

            if self.steam.login(username=steam_login, password=steam_password):
                self.steam.change_status(persona_state=7)
                log.info('We successfully logged invis mode into Steam')
                self.dota.launch()
            else:
                log.info('Logging into Steam failed')
                return

    def get_app_command(
            self,
            value: Union[str, int]
    ) -> Optional[Tuple[str, int]]:

        for cmd_name, cmd_id in self.app_commands.items():
            if value == cmd_name or value.isdigit() and int(value) == cmd_id:
                return cmd_name, cmd_id

        return None

    async def update_app_commands_cache(
            self,
            *,
            commands: Optional[List[AppCommand]] = None,
            guild: Optional[Snowflake] = None
    ) -> None:
        if not commands:
            commands = await self.tree.fetch_commands(guild=guild.id if guild else None)
        self.app_commands = {cmd.name: cmd.id for cmd in commands}

    # Shortcuts

    @property
    def alu_guild(self):
        return self.get_guild(Sid.alu)

    @property
    def wink_guild(self):
        return self.get_guild(Sid.wink)

    @property
    def blush_guild(self):
        return self.get_guild(Sid.blush)

    # Image Tools
    @staticmethod
    def str_to_file(
            string: str,
            filename: str = "FromAluBot.txt"
    ) -> File:
        return imgtools.str_to_file(string, filename)

    @staticmethod
    def plt_to_file(
            fig,
            filename: str = 'FromAluBot.png'
    ) -> File:
        return imgtools.plt_to_file(fig, filename)

    @staticmethod
    def img_to_file(
            image,
            filename: str = 'FromAluBot.png',
            fmt: str = 'PNG'
    ) -> File:
        return imgtools.img_to_file(image, filename, fmt)

    async def url_to_img(
            self,
            url: Union[str, Sequence[str]],
            *,
            return_list: bool = False
    ):
        return await imgtools.url_to_img(self.__session, url, return_list=return_list)

    async def url_to_file(
            self,
            url: Union[str, Sequence[str]],
            filename: str = 'FromAluBot.png',
            *,
            return_list: bool = False
    ) -> Union[File, Sequence[File]]:
        return await imgtools.url_to_file(self.__session, url, filename, return_list=return_list)


class LogHandler(logging.StreamHandler):

    def __init__(self, papertrail=True):
        logging.StreamHandler.__init__(self)
        if papertrail:  # AluBot
            fmt = '%(filename)-15s|%(lineno)-4d| %(message)s'
            formatter = logging.Formatter(fmt)
            self.setFormatter(formatter)
            pass
        else:  # YenBot
            fmt = '%(levelname)-5.5s| %(filename)-15s|%(lineno)-4d|%(asctime)s| %(message)s'
            fmt_date = "%H:%M:%S"  # '%Y-%m-%dT%T%Z'
            formatter = logging.Formatter(fmt, fmt_date)
            self.setFormatter(formatter)