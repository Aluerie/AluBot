from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from ._enums import ChannelEnum, RoleEnum

if TYPE_CHECKING:
    from utils import AluBot

# guild id
HIDEOUT = 759916212842659850

class Chd(ChannelEnum):
    global_logs = 997149550324240465
    daily_report = 1066406466778566801

    spam_me = 970823670702411810
    test_spam = 1066379298363166791

    repost = 971504469995049041

    copy_dota_info = 873430376033452053
    copy_dota_steam = 881843565251141632
    copy_dota_tweets = 963954743644934184

    event_pass = 966316773869772860


class Rhd(RoleEnum):
    event = 1090274008680902667
    jailed_bots = 1090428532162822234


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

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(HIDEOUT)  # type: ignore

    # channels
    @property
    def global_logs(self) -> discord.TextChannel:
        return self.bot.get_channel(Chd.global_logs.id)  # type: ignore

    @property
    def daily_report(self) -> discord.TextChannel:
        return self.bot.get_channel(Chd.daily_report.id)  # type: ignore

    @property
    def spam_channel_id(self) -> int:
        return Chd.test_spam.id if self.bot.test else Chd.spam_me.id

    @property
    def spam(self) -> discord.TextChannel:
        return self.bot.get_channel(self.spam_channel_id)  # type: ignore

    @property
    def repost(self) -> discord.TextChannel:
        return self.bot.get_channel(Chd.repost.id)  # type: ignore

    @property
    def copy_dota_tweets(self) -> discord.TextChannel:
        return self.bot.get_channel(Chd.copy_dota_tweets.id)  # type: ignore

    # roles
    @property
    def jailed_bots(self) -> discord.Role:
        return self.guild.get_role(Rhd.jailed_bots.id)  # type: ignore
