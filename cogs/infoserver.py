from discord import Embed, app_commands
from discord.ext import commands
from discord.ext.commands import Range

from utils import database as db
from utils.var import *
from utils.discord import scnf


class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Info'

    async def rule_work(self, ctx, num, dtb, min_number):
        try:
            my_row = db.session.query(dtb).order_by(dtb.id).limit(num + min_number)[num - min_number]
            embed = Embed(colour=Clr.prpl, title=f'Rule {num}')
            embed.description = f'{num}. {my_row.text}'
            await ctx.reply(embed=embed)
        except:
            await ctx.reply(content='there is no such rule')

    @commands.hybrid_command(
        name='rule',
        brief=Ems.slash,
        description="Show rule number `num`"
    )
    @app_commands.describe(number="Enter a number")
    async def rule(self, ctx, number: Range[int, 1, 99]):
        """Show rule number `num`"""
        await self.rule_work(ctx, number, db.sr, 0)

    @commands.hybrid_command(
        name='realrule',
        brief=Ems.slash,
        description="Show *real rule* number `num`"
    )
    @app_commands.describe(number="Enter a number")
    async def realrule(self, ctx,number: Range[int, 1, 99]):
        """Show *real rule* number `num`"""
        await self.rule_work(ctx, number, db.rr, 1)

    async def rules_work(self, ctx, dtb, min_value):
        with db.session_scope() as ses:
            # min_value = ses.query(func.min(dtb.id)).scalar() wont work fine when people delete 1 id
            list_rules = [
                f'{counter}. {row.text}' for counter, row in enumerate(ses.query(dtb).order_by(dtb.id), start=min_value)
            ]
        embed = Embed(colour=Clr.prpl)
        embed.title = 'Server rules'
        embed.description = f'\n'.join(list_rules)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(
        name='rules',
        brief=Ems.slash,
        description="Show all rules of the server"
    )
    async def rules(self, ctx):
        """Show all rules of the server"""
        await self.rules_work(ctx, db.sr, 0)

    @commands.hybrid_command(
        name='realrules',
        brief=Ems.slash,
        description="Show all *real rules* of the server"
    )
    async def realrules(self, ctx):
        """Show all *real rules* of the server"""
        await self.rules_work(ctx, db.rr, 1)


class ModServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Rules'

    @commands.has_role(Rid.discord_mods)
    @commands.group()
    async def modrule(self, ctx):
        """Group command about rule modding, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @commands.has_role(Rid.discord_mods)
    @commands.group()
    async def modrealrule(self, ctx):
        """Group command about rule modding, for actual commands use it together with subcommands"""
        await scnf(ctx)

    async def add_work(self, ctx, text, dtb):
        db.append_row(dtb, text=text)
        await ctx.reply(content='added')

    @modrule.command()
    async def add(self, ctx, *, text: str):
        """Add rule to server rules"""
        await self.add_work(ctx, text, db.sr)

    @modrealrule.command(name='add')
    async def add2(self, ctx, *, text: str):
        """Add rule to *real rules*"""
        await self.add_work(ctx, text, db.rr)

    async def remove_work(self, ctx, num, dtb, min_number):
        with db.session_scope() as ses:
            my_row = ses.query(dtb).order_by(dtb.id).limit(num+min_number)[0]
            ses.query(dtb).filter_by(id=my_row.id).delete()
        await ctx.reply(content='removed')

    @modrule.command()
    async def remove(self, ctx, num: int):
        """Remove rule under number `num` from server rules"""
        await self.remove_work(ctx, num, db.sr, 0)

    @modrealrule.command(name='remove')
    async def remove2(self, ctx, num: int):
        """Remove rule under number `num` from *real rules*"""
        await self.remove_work(ctx, num, db.rr, 1)


async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
    await bot.add_cog(ModServerInfo(bot))
