from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import aluloop, const

from ._base import CommunityCog

if TYPE_CHECKING:
    from utils import AluBot, AluGuildContext

ORIGINAL_NAME = '\N{CINEMA}streaming_room'


class StreamChannelName(CommunityCog, name='\N{CINEMA}streaming\\_room Control', emote=const.Emote.peepoMovie):
    """Change streaming room title.

    Get folks ready to watch your stream with a fancy title \
    so everybody knows what you are streaming.
    """

    async def cog_load(self) -> None:
        self.check_voice_members.start()

    async def cog_unload(self) -> None:
        self.check_voice_members.cancel()

    @commands.Cog.listener('on_voice_state_update')
    async def community_voice_chat_logging(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.guild.id != self.community.id:
            return

        voice_role = self.bot.community.voice_role
        if before.channel is None and after.channel is not None:  # joined the voice channel
            await member.add_roles(voice_role)
            e = discord.Embed(color=0x00FF7F)
            msg = f'{member.display_name} entered {after.channel.name}.'
            e.set_author(name=msg, icon_url=member.display_avatar.url)
            await after.channel.send(embed=e)
            return
        if before.channel is not None and after.channel is None:  # quit the voice channel
            await member.remove_roles(voice_role)
            e = discord.Embed(color=0x800000)
            msg = f'{member.display_name} left {before.channel.name}.'
            e.set_author(name=msg, icon_url=member.display_avatar.url)
            await before.channel.send(embed=e)
            return
        if before.channel is not None and after.channel is not None:  # changed voice channels
            if before.channel.id != after.channel.id:
                e = discord.Embed(color=0x6495ED)
                msg = f'{member.display_name} went from {before.channel.name} to {after.channel.name}.'
                e.set_author(name=msg, icon_url=member.display_avatar.url)
                await before.channel.send(embed=e)
                await after.channel.send(embed=e)
                return

    @app_commands.guilds(const.Guild.community)
    @commands.hybrid_group(
        name='streaming-room',
        aliases=['stream'],
        description="Commands about managing #\N{CINEMA}streaming_room voice channel title.",
    )
    async def streaming_room(self, ctx: AluGuildContext):
        """Commands about managing **#\N{CINEMA}streaming_room** voice channel title."""
        await ctx.send_help(ctx.command)

    @commands.cooldown(1, 15 * 60, commands.BucketType.guild)
    @streaming_room.command(
        name='title',
        description="Sets title for #\N{CINEMA}streaming_room so people know what you are streaming.",
    )
    @app_commands.describe(text=f'new title for #{ORIGINAL_NAME}')
    async def title(self, ctx: AluGuildContext, *, text: str):
        """Sets title for **#\N{CINEMA}streaming_room** so people know what you are streaming."""
        new_name = f'\N{CINEMA}{text}'
        await self.community.stream_room.edit(name=new_name)
        e = discord.Embed(colour=const.Colour.prpl())
        e.description = f'Changed title of **#{ORIGINAL_NAME}** to **#{new_name}**'
        await ctx.reply(embed=e)

    @commands.cooldown(1, 15 * 60, commands.BucketType.guild)
    @streaming_room.command(
        name='reset',
        description="Reset #\N{CINEMA}streaming_room title.",
    )
    async def reset(self, ctx: AluGuildContext):
        """Reset **#\N{CINEMA}streaming_room** title."""
        await self.community.stream_room.edit(name=ORIGINAL_NAME)
        e = discord.Embed(colour=const.Colour.prpl())
        e.description = f'Title of **#{ORIGINAL_NAME}** has been reset'
        await ctx.reply(embed=e)

    @aluloop(count=1)
    async def check_voice_members(self):
        voice_role = self.community.voice_role
        for member in voice_role.members:
            if member.voice is None:
                await member.remove_roles(voice_role)


async def setup(bot: AluBot):
    await bot.add_cog(StreamChannelName(bot))
