from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from discord import Embed, Guild, Member, Object, utils, HTTPException
from discord.ext import commands
from discord.ext.commands import Greedy

from utils import database as db
from utils.checks import is_owner
from utils.var import *
from utils.context import Context


if TYPE_CHECKING:
    pass


class AdminTools(commands.Cog, name='Tools for Bot Owner'):
    """
    Commands for admin tools
    """
    def __init__(self, bot):
        self.bot = bot
        self.help_emote = Ems.Lewd

    @is_owner()
    @commands.command()
    async def msgcount(self, ctx, member: Member, msg_count):
        db.set_value(db.m, member.id, msg_count=msg_count)
        embed = Embed(colour=member.colour)
        embed.description = f'msgcount: {member.mention} (id=`{member.id}`) to `{msg_count}`! {Ems.bubuAyaya}'
        await ctx.channel.send(embed=embed)

    @is_owner()
    @commands.command()
    async def leaveguild(self, ctx, guild: Guild):
        """'Make bot leave guild with named guild_id;"""
        embed = Embed(colour=Clr.prpl)
        if guild is not None:
            await guild.leave()
            embed.description = f'Just left guild {guild.name} with id `{guild.id}`\n'
        else:
            embed.description = f'The bot is not in the guild with id `{guild}`'
        await ctx.reply(embed=embed)

    @is_owner()
    @commands.command()
    async def guildlist(self, ctx):
        """Show list of guilds bot is in ;"""
        embed = Embed(
            colour=Clr.prpl,
            description=
            f"The bot is in these guilds\n"
            f"{chr(10).join([f'• {item.name} `{item.id}`' for item in self.bot.guilds])}"
        )
        await ctx.reply(embed=embed)

    @is_owner()
    @commands.command()
    async def purgelist(self, ctx: commands.Context, msgid_last: int, msgid_first: int):
        """Delete messages between given ids in current channel ;"""
        temp_purge_list = []
        async for msg in ctx.channel.history(limit=2000):
            if msgid_first < msg.id < msgid_last:
                temp_purge_list.append(msg)

        split_size = 90
        msg_split_list = [temp_purge_list[x:x + split_size] for x in range(0, len(temp_purge_list), split_size)]
        for item in msg_split_list:
            await ctx.channel.delete_messages(item)
        await ctx.reply('Done', delete_after=10)

    @is_owner()
    @commands.command()
    async def emotecredits(self, ctx):
        """emote credits"""
        guild = self.bot.get_guild(Sid.alu)
        rules_channel = guild.get_channel(Cid.rules)
        msg = rules_channel.get_partial_message(866006902458679336)
        embed = Embed(color=Clr.prpl)
        emote_names = ['bubuChrist', 'bubuGunGun', 'PepoBeliever', 'cocoGunGun', 'iofibonksfast']
        emote_array = [utils.get(guild.emojis, name=item) for item in emote_names]
        embed.title = 'Credits for following emotes'
        embed.description = '''
        ● [twitch.tv/bububu](https://www.twitch.tv/bububu)
        {0} {1} {2}
        ● [twitch.tv/khezu](https://www.twitch.tv/khezu)
        {3}  
        ● [chroneco.moe](https://www.chroneco.moe/)
        {4} {5}
        '''.format(*emote_array)
        await msg.edit(content='', embed=embed)
        await ctx.reply(f"we did it {Ems.PogChampPepe}")

    @is_owner()
    @commands.command()
    async def sync(self, ctx: Context, guilds: Greedy[Object], spec: Optional[Literal["~", "*"]] = None) -> None:
        """
        `$sync` -> global sync
        `$sync ~` -> sync current guild
        `$sync *` -> copies all global app commands to current guild and syncs
        `$sync id_1 id_2` -> syncs guilds with id 1 and 2
        """
        if not guilds:
            if spec == "~":
                fmt = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                fmt = await ctx.bot.tree.sync(guild=ctx.guild)
            else:
                fmt = await ctx.bot.tree.sync()

            await ctx.send(f"Synced {len(fmt)} commands {'globally' if spec is None else 'to the current guild.'}")
            return

        fmt = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except HTTPException:
                pass
            else:
                fmt += 1

        await ctx.send(f"Synced the tree to {fmt}/{len(guilds)} guilds.")


async def setup(bot):
    await bot.add_cog(AdminTools(bot))
