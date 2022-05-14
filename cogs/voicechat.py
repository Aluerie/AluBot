from discord import Embed, option
from discord.ext import commands, tasks, bridge

from utils.var import *


class Voicechat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_voice_members.start()
        self.help_category = 'Tools'

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.guild.id != Sid.irene:
            return
        irene_server = self.bot.get_guild(Sid.irene)
        voice_role = irene_server.get_role(Rid.voice)
        text_for_vc = irene_server.get_channel(Cid.text_for_vc)
        if before.channel is None and after.channel is not None:  # joined the voice channel
            await member.add_roles(voice_role)
            embed = Embed(color=0x00ff7f)
            text = f'{member.display_name} entered {after.channel.name}'
            embed.set_author(name=text, icon_url=member.display_avatar.url)
            return await text_for_vc.send(embed=embed)
        if before.channel is not None and after.channel is None:  # quit the voice channel
            await member.remove_roles(voice_role)
            embed = Embed(color=0x800000)
            text = f'{member.display_name} left {before.channel.name}'
            embed.set_author(name=text, icon_url=member.display_avatar.url)
            return await text_for_vc.send(embed=embed)
        if before.channel is not None and after.channel is not None:  # changed voice channels
            if before.channel.id != after.channel.id:
                embed = Embed(color=0x6495ed)
                text = f'{member.display_name} went from {before.channel.name} to {after.channel.name}'
                embed.set_author(name=text, icon_url=member.display_avatar.url)
                return await text_for_vc.send(embed=embed)

    # @commands.has_any_role(Rid.voice)
    @commands.cooldown(1, 15 * 60, commands.BucketType.guild)
    @bridge.bridge_command(
        name='settitle',
        description='Set title for #🎦streaming room so people know what you are streaming',
        brief=Ems.slash
    )
    @option('text', description='new title for #streaming_room')
    async def settitle(self, ctx, *, text: str):
        """Sets title for **#🎦streaming_room** so people know what you are streaming ;"""
        new_name = f'🎦{text}'
        irene_server = self.bot.get_guild(Sid.irene)
        await irene_server.get_channel(Cid.stream_room).edit(name=new_name)
        embed = Embed(colour=Clr.prpl)
        embed.description = f'Changed title of **#🎦streaming_room** to **#{new_name}**'
        await ctx.respond(embed=embed)

    @commands.cooldown(1, 15 * 60, commands.BucketType.guild)
    @bridge.bridge_command(
        name='resettitle',
        description='Reset #🎦streaming_room title',
        brief=Ems.slash
    )
    async def resettitle(self, ctx):
        """Reset **#🎦streaming_room** title ;"""
        irene_server = self.bot.get_guild(Sid.irene)
        original_name = '🎦streaming_room'
        await irene_server.get_channel(Cid.stream_room).edit(name=original_name)
        embed = Embed(colour=Clr.prpl)
        embed.description = f'Title of **#{original_name}** has been reset'
        await ctx.respond(embed=embed)

    @tasks.loop(count=1)
    async def check_voice_members(self):
        irene_server = self.bot.get_guild(Sid.irene)
        voice_role = irene_server.get_role(Rid.voice)
        for member in voice_role.members:
            if member.voice is None:
                await member.remove_roles(voice_role)

    @check_voice_members.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Voicechat(bot))
