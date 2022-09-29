from __future__ import annotations

from os import listdir
from typing import TYPE_CHECKING, Optional

from discord import Embed, Guild, Member, Object, utils, HTTPException
from discord.ext import commands, tasks
from discord.ext.commands import Greedy

from utils import database as db
from utils.checks import is_owner
from utils.var import *
from utils.bot import test_list, YEN_JSK
from utils.context import Context

if TYPE_CHECKING:
    from utils.bot import AluBot


class AdminTools(commands.Cog, name='Tools for Bot Owner'):
    """
    Commands for admin tools
    """
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.help_emote = Ems.Lewd
        self.checkguilds.start()

    def cog_unload(self) -> None:
        self.checkguilds.cancel()

    @is_owner()
    @commands.command(hidden=True)
    async def msgcount(self, ctx, member: Member, msg_count):
        db.set_value(db.m, member.id, msg_count=msg_count)
        embed = Embed(
            colour=member.colour,
            description=f'msgcount: {member.mention} (id=`{member.id}`) to `{msg_count}`! {Ems.bubuAyaya}'
        )
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
        """
        Show list of guilds bot is in.
        """
        embed = Embed(
            colour=Clr.prpl,
            description=
            f"The bot is in these guilds\n"
            f"{chr(10).join([f'• {item.name} `{item.id}`' for item in self.bot.guilds])}"
        )
        await ctx.reply(embed=embed)

    @is_owner()
    @commands.command()
    async def purgelist(self, ctx: Context, msgid_last: int, msgid_first: int):
        """
        Delete messages between given ids in current channel.
        """
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
    async def emotecredits(self, ctx: Context):
        """emote credits"""
        guild = self.bot.get_guild(Sid.alu)
        rules_channel = guild.get_channel(Cid.rules)
        msg = rules_channel.get_partial_message(866006902458679336)

        emote_names = ['bubuChrist', 'bubuGunGun', 'PepoBeliever', 'cocoGunGun', 'iofibonksfast']
        emote_array = [utils.get(guild.emojis, name=item) for item in emote_names]
        em = Embed(
            color=Clr.prpl,
            title='Credits for following emotes',
            description=
            '''
            ● [twitch.tv/bububu](https://www.twitch.tv/bububu)
            {0} {1} {2}
            ● [twitch.tv/khezu](https://www.twitch.tv/khezu)
            {3}  
            ● [chroneco.moe](https://www.chroneco.moe/)
            {4} {5}
            '''.format(*emote_array)
        )
        await msg.edit(content='', embed=em)
        await ctx.reply(f"we did it {Ems.PogChampPepe}")

    async def guild_check_work(self, guild):
        trusted_ids = db.get_value(db.b, Sid.alu, 'trusted_ids')
        if guild.owner_id not in trusted_ids:
            def find_txt_channel():
                if guild.system_channel.permissions_for(guild.me).send_messages:
                    return guild.system_channel
                else:
                    for ch in guild.text_channels:
                        perms = ch.permissions_for(guild.me)
                        if perms.send_messages:
                            return ch
            em = Embed(
                colour=Clr.prpl,
                title='Do not invite me to other guilds, please',
                description=
                f"Sorry, I don't like being in guilds that aren't made by Aluerie.\n\nI'm leaving."
            ).set_footer(
                text=
                f'If you really want the bot in your server - '
                f'then dm {self.bot.owner} with good reasoning',
                icon_url=self.bot.owner.avatar.url
            )
            await find_txt_channel().send(embed=em)
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

    @is_owner()
    @commands.group()
    async def trustee(self, ctx: Context):
        await ctx.scnf()

    @staticmethod
    async def trustee_add_remove(
            ctx: Context,
            user_id: int,
            mode: Literal['add', 'remov']
    ):
        trusted_ids: list = db.get_value(db.b, Sid.alu, 'trusted_ids')
        if mode == 'add':
            trusted_ids.append(user_id)
        elif mode == 'remov':
            trusted_ids.remove(user_id)
        db.set_value(db.b, Sid.alu, trusted_ids=trusted_ids)
        em = Embed(
            colour=Clr.prpl,
            description=
            f'We {mode}ed user with id {user_id} to the list of trusted users'
        )
        await ctx.reply(embed=em)

    @is_owner()
    @trustee.command()
    async def add(self, ctx: Context, user_id: int):
        """
        Grant trustee privilege to a user with `user_id`.
        Trustees can add my bot to their servers and use commands that interact with the bot's database.
        """
        await self.trustee_add_remove(ctx, user_id=user_id, mode='add')

    @is_owner()
    @trustee.command()
    async def remove(self, ctx: Context, user_id: int):
        """
        Remove trustee privilege from a user with `user_id`.
        """
        await self.trustee_add_remove(ctx, user_id=user_id, mode='remov')

    @is_owner()
    @commands.command()
    async def sync(
            self,
            ctx: Context,
            guilds: Greedy[Object],
            spec: Optional[Literal["~", "*"]] = None
    ) -> None:
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

            await ctx.send(
                f"Synced {len(fmt)} commands "
                f"{'globally' if spec is None else 'to the current guild.'}"
            )
            await self.bot.update_app_commands_cache(commands=fmt)
            return

        fmt = 0
        cmds = []
        for guild in guilds:
            try:
                cmds += await ctx.bot.tree.sync(guild=guild)
            except HTTPException:
                pass
            else:
                fmt += 1
        await self.bot.update_app_commands_cache(commands=cmds)
        await ctx.send(f"Synced the tree to {fmt}/{len(guilds)} guilds.")

    @is_owner()
    @commands.command(name='extensions', hidden=True)
    async def extensions(self, ctx: Context):
        """Shows available extensions to load/reload/unload."""
        cogs = [f'● {x[:-3]}' for x in listdir('./cogs') if x.endswith('.py')] + ['● jishaku']
        em = Embed(
            colour=Clr.prpl,
            title='Available Extensions',
            description='\n'.join(cogs)
        )
        await ctx.reply(embed=em)

    async def load_unload_reload_job(
            self,
            ctx: Context,
            module: str,
            *,
            mode: Literal['load', 'unload', 'reload']
    ):
        try:
            filename = f'cogs.{module.lower()}'  # so we do `$unload beta` instead of `$unload beta.py`
            match mode:
                case 'load':
                    await self.bot.load_extension(filename)
                case 'unload':
                    await self.bot.unload_extension(filename)
                case 'reload':
                    await self.bot.reload_extension(filename)
        except commands.ExtensionError as e:
            em = Embed(
                colour=Clr.error,
                description=f'{e}'
            ).set_author(
                name=e.__class__.__name__
            )
            await ctx.send(embed=em)
        else:
            await ctx.message.add_reaction(Ems.DankApprove)

    @is_owner()
    @commands.command(name='load', hidden=True)
    async def load(self, ctx: Context, *, module: str):
        """Loads a module."""
        await self.load_unload_reload_job(ctx, module, mode='load')

    @is_owner()
    @commands.command(name='unload', hidden=True)
    async def unload(self, ctx: Context, *, module: str):
        """Unloads a module."""
        await self.load_unload_reload_job(ctx, module, mode='unload')

    @is_owner()
    @commands.group(name='reload', hidden=True, invoke_without_command=True)
    async def reload(self, ctx: Context, *, module: str):
        """Reloads a module."""
        await self.load_unload_reload_job(ctx, module, mode='reload')

    async def reload_or_load_extension(self, module: str) -> None:
        try:
            await self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(module)

    @is_owner()
    @reload.command(name='all', hidden=True)
    async def reload_all(self, ctx: Context):
        """Reloads all modules"""
        cogs_to_reload = []
        if self.bot.yen and len(test_list):
            if YEN_JSK:
                cogs_to_reload.append('jishaku')
            for item in test_list:
                cogs_to_reload.append(f'cogs.{item}')
        else:
            cogs_to_reload.append('jishaku')
            for filename in listdir('./cogs'):
                if filename.endswith('.py'):
                    cogs_to_reload.append(f'cogs.{filename[:-3]}')

        add_reaction = True
        for cog in cogs_to_reload:
            try:
                await self.reload_or_load_extension(cog)
            except commands.ExtensionError as e:
                await ctx.send(f'{e.__class__.__name__}: {e}')
                add_reaction = False
        if add_reaction:
            await ctx.message.add_reaction(Ems.DankApprove)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != Sid.blush:
            return
        if member.bot:
            bots_role = member.guild.get_role(Rid.waste_bots_role)
            await member.add_roles(bots_role)


async def setup(bot):
    await bot.add_cog(AdminTools(bot))
