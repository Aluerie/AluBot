from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils import AluCog, Clr, Ems, Sid


if TYPE_CHECKING:
    from utils import AluBot, AluContext

ORIGINAL_NAME = '\N{CINEMA}streaming_room'


class StreamChannelName(AluCog, name='\N{CINEMA}streaming_room Control', emote=Ems.peepoMovie):
    """Change streaming room title

    Get folks ready to watch your stream with a fancy title \
    so everybody knows what you are streaming.
    """

    async def cog_load(self) -> None:
        self.check_voice_members.start()

    async def cog_unload(self) -> None:
        self.check_voice_members.cancel()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if member.guild.id != self.community.id:
            return

        voice_role = self.bot.community.voice_role
        if before.channel is None and after.channel is not None:  # joined the voice channel
            await member.add_roles(voice_role)
            e = discord.Embed(color=0x00FF7F)
            e.set_author(name=f'{member.display_name} entered {after.channel.name}', icon_url=member.display_avatar.url)
            return await after.channel.send(embed=e)
        if before.channel is not None and after.channel is None:  # quit the voice channel
            await member.remove_roles(voice_role)
            e = discord.Embed(color=0x800000)
            e.set_author(name=f'{member.display_name} left {before.channel.name}', icon_url=member.display_avatar.url)
            return await before.channel.send(embed=e)
        if before.channel is not None and after.channel is not None:  # changed voice channels
            if before.channel.id != after.channel.id:
                e = discord.Embed(color=0x6495ED)
                e.set_author(
                    name=f'{member.display_name} went from {before.channel.name} to {after.channel.name}',
                    icon_url=member.display_avatar.url,
                )
                await before.channel.send(embed=e)
                return await after.channel.send(embed=e)

    @app_commands.guilds(Sid.community)
    @commands.hybrid_group(name='streaming-room', aliases=['stream'])
    async def streaming_room(self, ctx: AluContext):
        """Group command about Dota, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @commands.cooldown(1, 15 * 60, commands.BucketType.guild)
    @streaming_room.command(
        name='title', description=f'Set title for #{ORIGINAL_NAME} so people know what you are streaming'
    )
    @app_commands.describe(text=f'new title for #{ORIGINAL_NAME}')
    async def title(self, ctx: AluContext, *, text: str):
        """Sets title for **#\N{CINEMA}streaming_room** so people know what you are streaming"""
        new_name = f'\N{CINEMA}{text}'
        await self.bot.community.stream_room.edit(name=new_name)
        e = discord.Embed(description=f'Changed title of **#{ORIGINAL_NAME}** to **#{new_name}**', colour=Clr.prpl)
        await ctx.reply(embed=e)

    @commands.cooldown(1, 15 * 60, commands.BucketType.guild)
    @streaming_room.command(name='reset')
    async def reset(self, ctx: AluContext):
        """Reset **#\N{CINEMA}streaming_room** title ;"""
        await self.bot.community.stream_room.edit(name=ORIGINAL_NAME)
        e = discord.Embed(description=f'Title of **#{ORIGINAL_NAME}** has been reset', colour=Clr.prpl)
        await ctx.reply(embed=e)

    @tasks.loop(count=1)
    async def check_voice_members(self):
        voice_role = self.bot.community.voice_role
        for member in voice_role.members:
            if member.voice is None:
                await member.remove_roles(voice_role)

    @check_voice_members.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(StreamChannelName(bot))
