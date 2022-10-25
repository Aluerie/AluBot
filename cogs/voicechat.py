from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Embed, Member, app_commands
from discord.ext import commands, tasks

from utils.var import *

if TYPE_CHECKING:
    from utils.bot import AluBot, Context

ORIGINAL_NAME = '🎦streaming_room'


class VoiceChat(commands.Cog, name='Voice Chat'):
    """
    Change streaming room title

    Get folks ready to watch your stream with a fancy title \
    so everybody knows what you are streaming.
    """

    def __init__(self, bot):
        self.bot: AluBot = bot
        self.check_voice_members.start()
        self.help_emote = Ems.peepoMovie

    def cog_unload(self) -> None:
        self.check_voice_members.cancel()

    @commands.Cog.listener()
    async def on_voice_state_update(self, mbr: Member, before, after):
        if mbr.guild.id != Sid.alu:
            return
        guild = self.bot.get_guild(Sid.alu)
        voice_role = guild.get_role(Rid.voice)
        if before.channel is None and after.channel is not None:  # joined the voice channel
            await mbr.add_roles(voice_role)
            em = Embed(
                color=0x00ff7f
            ).set_author(
                name=f'{mbr.display_name} entered {after.channel.name}',
                icon_url=mbr.display_avatar.url
            )
            return await after.channel.send(embed=em)
        if before.channel is not None and after.channel is None:  # quit the voice channel
            await mbr.remove_roles(voice_role)
            em = Embed(
                color=0x800000
            ).set_author(
                name=f'{mbr.display_name} left {before.channel.name}',
                icon_url=mbr.display_avatar.url
            )
            return await before.channel.send(embed=em)
        if before.channel is not None and after.channel is not None:  # changed voice channels
            if before.channel.id != after.channel.id:
                em = Embed(
                    color=0x6495ed
                ).set_author(
                    name=f'{mbr.display_name} went from {before.channel.name} to {after.channel.name}',
                    icon_url=mbr.display_avatar.url
                )
                await before.channel.send(embed=em)
                return await after.channel.send(embed=em)

    @app_commands.guilds(Sid.alu)
    @commands.hybrid_group(
        name='streaming-room',
        aliases=['stream']
    )
    async def streaming_room(self, ctx: Context):
        """Group command about Dota, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @commands.cooldown(1, 15 * 60, commands.BucketType.guild)
    @streaming_room.command(
        name='title',
        description=f'Set title for #{ORIGINAL_NAME} so people know what you are streaming'
    )
    @app_commands.describe(text=f'new title for #{ORIGINAL_NAME}')
    async def title(self, ctx: Context, *, text: str):
        """Sets title for **#🎦streaming_room** so people know what you are streaming ;"""
        new_name = f'🎦{text}'
        guild = self.bot.get_guild(Sid.alu)
        await guild.get_channel(Cid.stream_room).edit(name=new_name)
        em = Embed(colour=Clr.prpl, description=f'Changed title of **#{ORIGINAL_NAME}** to **#{new_name}**')
        await ctx.reply(embed=em)

    @commands.cooldown(1, 15 * 60, commands.BucketType.guild)
    @streaming_room.command(
        name='reset',
        description=f'Reset #{ORIGINAL_NAME} title'
    )
    async def reset(self, ctx: Context):
        """Reset **#🎦streaming_room** title ;"""
        guild = self.bot.get_guild(Sid.alu)
        await guild.get_channel(Cid.stream_room).edit(name=ORIGINAL_NAME)
        em = Embed(colour=Clr.prpl, description=f'Title of **#{ORIGINAL_NAME}** has been reset')
        await ctx.reply(embed=em)

    @tasks.loop(count=1)
    async def check_voice_members(self):
        guild = self.bot.get_guild(Sid.alu)
        voice_role = guild.get_role(Rid.voice)
        for member in voice_role.members:
            if member.voice is None:
                await member.remove_roles(voice_role)

    @check_voice_members.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(VoiceChat(bot))
