from __future__ import annotations
from typing import TYPE_CHECKING, Union, Optional

from discord import Streaming, Intents, AllowedMentions
from discord.ext import commands

from utils.context import Context
from utils.mysteam import sd_login

from steam.client import SteamClient
from dota2.client import Dota2Client
from aiohttp import ClientSession
from datetime import datetime, timezone
from os import getenv, environ, listdir
import logging

if TYPE_CHECKING:
    from discord import Interaction, Message

jsk = True
test_list = [  # for yen bot
    'voicechat',
    'error'
]


class VioletBot(commands.Bot):
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
        self._help2_command = None
        self._help3_command = None
        self.yen = yen

    async def setup_hook(self) -> None:
        self.__session = ClientSession()
        if self.yen and (not len(test_list) or any(item in test_list for item in ['dotafeed', 'gamerstats'])):
            self.steam = SteamClient()
            self.dota = Dota2Client(self.steam)
            self.steam_lgn = getenv("STEAM_TEST_LGN")
            self.steam_psw = getenv("STEAM_TEST_PSW")
            sd_login(self.steam, self.dota, self.steam_lgn, self.steam_psw)
        elif self.yen:
            pass
        else:
            self.steam = SteamClient()
            self.dota = Dota2Client(self.steam)
            self.steam_lgn = getenv("STEAM_LGN")
            self.steam_psw = getenv("STEAM_PSW")
            sd_login(self.steam, self.dota, self.steam_lgn, self.steam_psw)

        if self.yen and len(test_list):
            if jsk:
                await self.load_cog('jishaku')
            for item in test_list:
                await self.load_cog(f'cogs.{item}')
        else:
            await self.load_cog('jishaku')
            for filename in listdir('./cogs'):
                if filename.endswith('.py'):
                    await self.load_cog(f'cogs.{filename[:-3]}')
        environ["JISHAKU_NO_UNDERSCORE"] = "True"

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
        environ["JISHAKU_NO_UNDERSCORE"] = "True"

    @property
    def ses(self):
        if self.__session.closed:
            self.__session = ClientSession()
        return self.__session

    @property
    def help2_command(self) -> Optional[commands.HelpCommand]:
        return self._help2_command

    @help2_command.setter
    def help2_command(self, value: Optional[commands.HelpCommand]) -> None:
        if value is not None:
            if not isinstance(value, commands.HelpCommand):
                raise TypeError("help2_command must be a subclass of HelpCommand")
            if self._help2_command is not None:
                self._help2_command._remove_from_bot(self)
            self._help2_command = value
            value._add_to_bot(self)
        elif self._help2_command is not None:
            self._help2_command._remove_from_bot(self)
            self._help2_command = None
        else:
            self._help2_command = None

    @property
    def help3_command(self) -> Optional[commands.HelpCommand]:
        return self._help3_command

    @help3_command.setter
    def help3_command(self, value: Optional[commands.HelpCommand]) -> None:
        if value is not None:
            if not isinstance(value, commands.HelpCommand):
                raise TypeError("help3_command must be a subclass of HelpCommand")
            if self._help3_command is not None:
                self._help3_command._remove_from_bot(self)
            self._help3_command = value
            value._add_to_bot(self)
        elif self._help3_command is not None:
            self._help3_command._remove_from_bot(self)
            self._help3_command = None
        else:
            self._help3_command = None

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
