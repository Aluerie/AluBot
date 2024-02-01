from __future__ import annotations

import contextlib
import random
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import const

from ._base import CommunityCog


class CommunityFun(CommunityCog):
    @staticmethod
    def community_check(msg: discord.Message) -> bool:
        if (
            msg.guild
            and msg.guild.id == const.Guild.community
            and not (msg.author.id in const.MY_BOTS or msg.webhook_id)  # webhook so we ignore dota-news or nqn bot
        ):
            return True
        else:
            return False

    @staticmethod
    def channel_check(msg: discord.Message, channel_id: int) -> bool:
        return bool(msg.channel.id == channel_id and msg.author.id not in const.MY_BOTS)

    @commands.Cog.listener("on_message")
    async def bots_in_lobby(self, message: discord.Message) -> None:
        if not self.channel_check(message, const.Channel.general):
            return

        if message.interaction is not None and message.interaction.type == discord.InteractionType.application_command:
            text = "Slash-commands"
        elif message.author.bot and not message.webhook_id:
            text = "Bots"
        else:
            return
        await message.channel.send(
            f"{text} in {const.Channel.general.mention} ! {const.Emote.Ree} {const.Emote.Ree} {const.Emote.Ree}"
        )

    @commands.Cog.listener("on_message")
    async def weebs_out(self, message: discord.Message) -> None:
        if not self.channel_check(message, const.Channel.weebs):
            return

        if random.randint(1, 100 + 1) < 7:
            await message.channel.send(
                "{0} {0} {0} {1} {1} {1} {2} {2} {2} {3} {3} {3}".format(
                    const.Emote.WeebsOutOut, const.Emote.WeebsOut, const.Emote.peepoWeebSmash, const.Emote.peepoRiot
                )
            )

    @commands.Cog.listener("on_message")
    async def ree_the_oof(self, message: discord.Message) -> None:
        if not self.community_check(message):
            return

        if "Oof" in message.content:
            try:
                await message.add_reaction(const.Emote.Ree)
            except discord.HTTPException:
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()

    @commands.Cog.listener("on_message")
    async def random_comfy_react(self, message: discord.Message) -> None:
        if not self.community_check(message):
            return

        roll = random.randint(1, 300 + 1)
        if roll < 2:
            try:
                await message.add_reaction(const.Emote.peepoComfy)
            except discord.HTTPException:
                return

    @commands.Cog.listener("on_message")
    async def your_life(self, message: discord.Message) -> None:
        if not self.community_check(message):
            return

        if random.randint(1, 170 + 1) < 2:
            try:
                sliced_text = message.content.split()
                if 13 > len(sliced_text) > 2:
                    answer_text = "Your life " + " ".join(sliced_text[2:])
                    await message.channel.send(answer_text)
            except Exception:
                return


async def setup(bot) -> None:
    await bot.add_cog(CommunityFun(bot))
