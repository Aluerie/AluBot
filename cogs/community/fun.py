from __future__ import annotations

import random
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import AluCog, const

if TYPE_CHECKING:
    pass


class CommunityFun(AluCog):
    @staticmethod
    def non_community_check(message: discord.Message):
        if message.author.id in const.MY_BOTS:
            return True
        if not message.guild or message.guild.id != const.Guild.community:
            return True
        return False

    @staticmethod
    def non_channel_check(message: discord.Message, channel_id: int):
        return message.author.id in const.MY_BOTS or message.channel.id != channel_id

    @commands.Cog.listener('on_message')
    async def bots_in_lobby(self, message: discord.Message):
        if self.non_channel_check(message, const.Channel.general):
            return

        if message.interaction is not None and message.interaction.type == discord.InteractionType.application_command:
            text = 'Slash-commands'
        elif message.author.bot and not message.webhook_id:
            text = 'Bots'
        else:
            return
        await message.channel.send(
            '{0} in {1} ! {2} {2} {2}'.format(text, const.Channel.general.mention, const.Emote.Ree)
        )

    @commands.Cog.listener('on_message')
    async def weebs_out(self, message: discord.Message):
        if self.non_channel_check(message, const.Channel.weebs):
            return

        if random.randint(1, 100 + 1) < 7:
            await message.channel.send(
                '{0} {0} {0} {1} {1} {1} {2} {2} {2} {3} {3} {3}'.format(
                    '<a:WeebsOutOut:730882034167185448>',
                    '<:WeebsOut:856985447985315860>',
                    '<a:peepoWeebSmash:728671752414167080>',
                    '<:peepoRiot:730883102678974491>',
                )
            )

    @commands.Cog.listener('on_message')
    async def ree_the_oof(self, message: discord.Message):
        if self.non_community_check(message):
            return

        if "Oof" in message.content:
            try:
                await message.add_reaction(const.Emote.Ree)
            except discord.errors.Forbidden:
                await message.delete()

    @commands.Cog.listener('on_message')
    async def random_comfy_react(self, message: discord.Message):
        if self.non_community_check(message):
            return

        roll = random.randint(1, 300 + 1)
        if roll < 2:
            try:
                await message.add_reaction(const.Emote.peepoComfy)
            except Exception:
                return

    @commands.Cog.listener('on_message')
    async def your_life(self, message: discord.Message):
        if self.non_community_check(message):
            return

        if random.randint(1, 170 + 1) < 2:
            try:
                sliced_text = message.content.split()
                if len(sliced_text) > 2:
                    answer_text = f"Your life {' '.join(sliced_text[2:])}"
                    await message.channel.send(answer_text)
            except Exception:
                return


async def setup(bot):
    await bot.add_cog(CommunityFun(bot))
