from discord import Embed, Member, app_commands
from discord.ext import commands, tasks

from utils.var import *


class Voicechat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_voice_members.start()
        self.help_category = 'Tools'

    @commands.Cog.listener()
    async def on_voice_state_update(self, mbr: Member, before, after):
        if mbr.guild.id != Sid.irene:
            return
        irene_server = self.bot.get_guild(Sid.irene)
        voice_role = irene_server.get_role(Rid.voice)
        text_for_vc = irene_server.get_channel(Cid.text_for_vc)
        if before.channel is None and after.channel is not None:  # joined the voice channel
            await mbr.add_roles(voice_role)
            em = Embed(color=0x00ff7f)
            em.set_author(name=f'{mbr.display_name} entered {after.channel.name}', icon_url=mbr.display_avatar.url)
            return await text_for_vc.send(embed=em)
        if before.channel is not None and after.channel is None:  # quit the voice channel
            await mbr.remove_roles(voice_role)
            em = Embed(color=0x800000)
            em.set_author(name=f'{mbr.display_name} left {before.channel.name}', icon_url=mbr.display_avatar.url)
            return await text_for_vc.send(embed=em)
        if before.channel is not None and after.channel is not None:  # changed voice channels
            if before.channel.id != after.channel.id:
                em = Embed(color=0x6495ed)
                em.set_author(
                    name=f'{mbr.display_name} went from {before.channel.name} to {after.channel.name}',
                    icon_url=mbr.display_avatar.url
                )
                return await text_for_vc.send(embed=em)

    @commands.has_role(Rid.voice)
    @commands.cooldown(1, 15 * 60, commands.BucketType.guild)
    @commands.hybrid_command(
        name='settitle',
        brief=Ems.slash,
        description='Set title for #🎦streaming room so people know what you are streaming'
    )
    @app_commands.describe(text='new title for #🎦streaming_room')
    async def settitle(self, ctx, *, text: str):
        """Sets title for **#🎦streaming_room** so people know what you are streaming ;"""
        new_name = f'🎦{text}'
        irene_server = self.bot.get_guild(Sid.irene)
        await irene_server.get_channel(Cid.stream_room).edit(name=new_name)
        em = Embed(colour=Clr.prpl)
        em.description = f'Changed title of **#🎦streaming_room** to **#{new_name}**'
        await ctx.reply(embed=em)

    @commands.cooldown(1, 15 * 60, commands.BucketType.guild)
    @commands.hybrid_command(
        name='resettitle',
        brief=Ems.slash,
        description='Reset #🎦streaming_room title'
    )
    async def resettitle(self, ctx):
        """Reset **#🎦streaming_room** title ;"""
        irene_server = self.bot.get_guild(Sid.irene)
        original_name = '🎦streaming_room'
        await irene_server.get_channel(Cid.stream_room).edit(name=original_name)
        em = Embed(colour=Clr.prpl, description = f'Title of **#{original_name}** has been reset')
        await ctx.reply(embed=em)

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


async def setup(bot):
    await bot.add_cog(Voicechat(bot))
