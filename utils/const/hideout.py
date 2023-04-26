from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from utils import AluBot

# guild id
HIDEOUT = 759916212842659850

# channel ids
# Remember that channel mentions are
# channel_mention = f'<#{REPOST}>'
GLOBAL_LOGS = 997149550324240465
DAILY_REPORT = 1066406466778566801

SPAM_ME = 970823670702411810
TEST_SPAM = 1066379298363166791

REPOST = 971504469995049041

COPY_DOTA_INFO = 873430376033452053
COPY_DOTA_STEAM = 881843565251141632
COPY_DOTA_TWEETS = 963954743644934184

EVENT_PASS = 966316773869772860

# role ids
# Remember that channel mentions are
# channel_mention = f'<@&{EVENT_ROLE}>'
EVENT_ROLE = 1090274008680902667
JAILED_BOTS = 1090428532162822234


class HideoutGuild:
    """
    My (probably wrong) way to combat
    absurd amount of "type: ignore" in the code
    with `get_channel` and similar methods for channels with known ids.

    This class basically mirrors my HideOut guild and tells the type checker
    known channels and their type, known roles, etc.
    """

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.test: bool = bot.test

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(HIDEOUT) # type: ignore

    # channels
    @property
    def global_logs(self) -> discord.TextChannel:
        return self.bot.get_channel(GLOBAL_LOGS)  # type: ignore

    @property
    def daily_report(self) -> discord.TextChannel:
        return self.bot.get_channel(DAILY_REPORT)  # type: ignore

    @property
    def spam_channel_id(self) -> int:
        return TEST_SPAM if self.test else SPAM_ME

    @property
    def spam(self) -> discord.TextChannel:
        return self.bot.get_channel(self.spam_channel_id)  # type: ignore

    @property
    def repost(self) -> discord.TextChannel:
        return self.bot.get_channel(REPOST)  # type: ignore

    @property
    def copy_dota_tweets(self) -> discord.TextChannel:
        return self.bot.get_channel(COPY_DOTA_TWEETS)  # type: ignore
    
    # roles
    @property
    def jailed_bots(self) -> discord.Role:
        return self.bot.get_role(JAILED_BOTS)  # type: ignore
