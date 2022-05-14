from discord import Embed, Guild, utils
from discord.ext import commands, tasks
from utils.var import *
from utils import database as db


class AdminTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'AdminTools'
        self.checkguilds.start()

    @commands.is_owner()
    @commands.command()
    async def msgcount(self, ctx, member_id, msg_count):
        db.set_value(db.m, member_id, msg_count=msg_count)
        await ctx.channel.send(content=f'Set msg_count of {member_id} to {msg_count}! {Ems.bubuAyaya}')

    @commands.is_owner()
    @commands.command()
    async def leaveguild(self, ctx, guild: Guild):
        """'Make bot leave guild with named guild_id;"""
        embed = Embed(colour=Clr.prpl)
        if guild is not None:
            await guild.leave()
            embed.description = f'Just left guild {guild.name} with id `{guild.id}`\n'
        else:
            embed.description = f'The bot is not in the guild with id `{guild}`'
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command()
    async def guildlist(self, ctx):
        """Show list of guilds bot is in ;"""
        embed = Embed(colour=Clr.prpl)
        embed.description = "The bot is in these guilds\n"
        embed.description += '• ' + '\n• '.join([f'{item.name} `{item.id}`' for item in self.bot.guilds])
        await ctx.send(embed=embed)

    @commands.has_permissions(administrator=True)
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
        await ctx.send('Done', delete_after=10)

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def emotecredits(self, ctx):
        """emote credits"""
        irene_server = self.bot.get_guild(Sid.irene)
        rules_channel = irene_server.get_channel(Cid.rules)
        msg = rules_channel.get_partial_message(866006902458679336)
        embed = Embed(color=Clr.prpl)
        emote_names = ['bubuChrist', 'bubuGunGun', 'PepoBeliever', 'cocoGunGun', 'iofibonksfast']
        emote_array = [utils.get(irene_server.emojis, name=item) for item in emote_names]
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
        await ctx.send(f"we did it {Ems.PogChampPepe}")

    async def guild_check_work(self, guild):
        if guild.owner_id not in [Uid.irene, Uid.bot]:
            def find_txt_channel():
                if guild.system_channel.permissions_for(guild.me).send_messages:
                    return guild.system_channel
                else:
                    for ch in guild.text_channels:
                        perms = ch.permissions_for(guild.me)
                        if perms.send_messages:
                            return ch
            embed = Embed(colour=Clr.prpl)
            embed.title = 'Do not invite me to other guilds, please'
            embed.description = \
                f"Sorry, I don't like being in guilds that aren't made by Irene.\n\nI'm leaving."
            await find_txt_channel().send(embed=embed)
            await guild.leave()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        await self.guild_check_work(guild)

    @tasks.loop(count=1)
    async def checkguilds(self):
        for guild in self.bot.guilds:
            await self.guild_check_work(guild)

    @checkguilds.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(AdminTools(bot))
