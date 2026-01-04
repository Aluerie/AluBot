from __future__ import annotations

import contextlib
import random
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot import AluCog
from utils import const

if TYPE_CHECKING:
    from bot import AluBot


__all__ = ("Chatter",)


class Chatter(AluCog):
    """Bot's chatter behavior features in community.

    Somewhat silly message-response based actions.
    """

    @staticmethod
    def community_server_check(msg: discord.Message) -> bool:
        """Whether the message is from the community server and author isn't a bot."""
        return (
            bool(msg.guild)
            and msg.guild.id == const.Guild.community
            and not (msg.author.id in const.MY_BOTS or msg.webhook_id)  # webhook to ignore dota-news or nqn bot
        )

    @staticmethod
    def channel_check(msg: discord.Message, channel_id: int) -> bool:
        """Whether the message's channel matches the check and author isn't MY bot."""
        return bool(msg.channel.id == channel_id and msg.author.id not in const.MY_BOTS)

    @commands.Cog.listener("on_message")
    async def bots_in_lobby(self, message: discord.Message) -> None:
        """Bot reacts to other bots' usage in #general with anger."""
        if not self.channel_check(message, const.Channel.general):
            return

        if message.interaction is not None and message.interaction.type == discord.InteractionType.application_command:
            text = "Slash-commands"
        elif message.author.bot and not message.webhook_id:
            text = "Bots"
        else:
            return

        content = f"{text} in {const.Channel.general.mention} ! Use {const.Channel.bot_spam.mention} {const.Emote.Ree}"
        await message.channel.send(content)

    @commands.Cog.listener("on_message")
    async def weebs_out(self, message: discord.Message) -> None:
        """Bot hates weebs therefore, weebs aren't allowed, even in #weebs_place."""
        if not self.channel_check(message, const.Channel.weebs):
            return

        if random.randint(1, 456 + 1) < 6:
            await message.channel.send(
                f"{const.Emote.WeebsOutOut} {const.Emote.WeebsOut} {const.Emote.peepoWeebSmash} {const.Emote.peepoRiot} ",
            )

    @commands.Cog.listener("on_message")
    async def ree_the_oof(self, message: discord.Message) -> None:
        """Bot hates when people say "Oof" so it reacts to it with angry emote."""
        if not self.community_server_check(message):
            return

        if "Oof" in message.content:
            try:
                await message.add_reaction(const.Emote.Ree)
            except discord.HTTPException:
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()

    @commands.Cog.listener("on_message")
    async def random_comfy_react(self, message: discord.Message) -> None:
        """Bot sometimes reacts to random messages with its favorite emote: peepoComfy."""
        if not self.community_server_check(message):
            return

        roll = random.randint(1, 3300 + 1)
        if roll < 2:
            try:
                await message.add_reaction(const.Emote.peepoComfy)
            except discord.HTTPException:
                return

    @commands.Cog.listener("on_message")
    async def your_life(self, message: discord.Message) -> None:
        """Bot sometimes does "Your mom" jokes but instead it's "Your life" joke."""
        if not self.community_server_check(message):
            return

        if random.randint(1, 299 + 1) < 2:
            with contextlib.suppress(Exception):
                sliced_text = message.content.split()
                if 13 > len(sliced_text) > 2:
                    answer_text = "Your life " + " ".join(sliced_text[2:])
                    await message.channel.send(answer_text)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Chatter(bot))
