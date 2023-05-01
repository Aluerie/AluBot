from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import Embed, app_commands
from discord.ext import commands
from discord.ext.commands import Range

from utils import Clr, Ems, Rid

if TYPE_CHECKING:
    from utils.bases.context import AluContext


class ServerInfo(commands.Cog, name='Rules'):
    """
    The Server has some strict rules

    Here you can see commands to view the rules or \
    edit them if you are a mod.
    """

    def __init__(self, bot):
        self.bot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.PepoRules)

    @staticmethod
    async def rule_work(ctx, num, dtb, min_number):
        try:
            my_row = db.session.query(dtb).order_by(dtb.id).limit(num + min_number)[num - min_number]
            e = Embed(colour=Clr.prpl(), title=f'Rule {num}')
            e.description = f'{num}. {my_row.text}'
            await ctx.reply(embed=e)
        except:
            await ctx.reply(content='there is no such rule')

    @commands.hybrid_command(name='rule', description="Show rule number `num`")
    @app_commands.describe(number="Enter a number")
    async def rule(self, ctx, number: Range[int, 0, 99]):
        """Show rule number `num`"""
        await self.rule_work(ctx, number, db.sr, 0)

    @commands.hybrid_command(name='realrule', description="Show *real rule* number `num`")
    @app_commands.describe(number="Enter a number")
    async def realrule(self, ctx, number: Range[int, 0, 99]):
        """Show *real rule* number `num`"""
        await self.rule_work(ctx, number, db.rr, 1)

    @staticmethod
    async def rules_work(ctx, dtb, min_value):
        with db.session_scope() as ses:
            # min_value = ses.query(func.min(dtb.id)).scalar() wont work fine when people delete 1 id
            list_rules = [
                f'{counter}. {row.text}' for counter, row in enumerate(ses.query(dtb).order_by(dtb.id), start=min_value)
            ]
        e = Embed(colour=Clr.prpl())
        e.title = 'Server rules'
        e.description = f'\n'.join(list_rules)
        await ctx.reply(embed=e)

    @commands.hybrid_command(name='rules', description="Show all rules of the server")
    async def rules(self, ctx):
        """Show all rules of the server"""
        await self.rules_work(ctx, db.sr, 0)

    @commands.hybrid_command(name='realrules', description="Show all *real rules* of the server")
    async def realrules(self, ctx):
        """Show all *real rules* of the server"""
        await self.rules_work(ctx, db.rr, 1)

    @commands.has_role(Rid.discord_mods)
    @commands.group()
    async def modrule(self, ctx: AluContext):
        """Group command about rule modding, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @commands.has_role(Rid.discord_mods)
    @commands.group()
    async def modrealrule(self, ctx: AluContext):
        """Group command about rule modding, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @staticmethod
    async def add_work(ctx, text, dtb):
        db.append_row(dtb, text=text)
        await ctx.reply(content='added')

    @commands.has_role(Rid.discord_mods)
    @modrule.command()
    async def add(self, ctx, *, text: str):
        """Add rule to server rules"""
        await self.add_work(ctx, text, db.sr)

    @commands.has_role(Rid.discord_mods)
    @modrealrule.command(name='add')
    async def add2(self, ctx, *, text: str):
        """Add rule to *real rules*"""
        await self.add_work(ctx, text, db.rr)

    @staticmethod
    async def remove_work(ctx, num, dtb, min_number):
        with db.session_scope() as ses:
            my_row = ses.query(dtb).order_by(dtb.id).limit(num + min_number)[0]
            ses.query(dtb).filter_by(id=my_row.id).delete()
        await ctx.reply(content='removed')

    @commands.has_role(Rid.discord_mods)
    @modrule.command()
    async def remove(self, ctx, num: int):
        """Remove rule under number `num` from server rules"""
        await self.remove_work(ctx, num, db.sr, 0)

    @commands.has_role(Rid.discord_mods)
    @modrealrule.command(name='remove')
    async def remove2(self, ctx, num: int):
        """Remove rule under number `num` from *real rules*"""
        await self.remove_work(ctx, num, db.rr, 1)


async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
