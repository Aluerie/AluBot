from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from discord import Interaction, Embed, Member, Message, app_commands
from discord.ext import commands
from discord.utils import format_dt, get

from utils.context import Context
from utils import database as db
from utils.var import *

from datetime import datetime, timezone

if TYPE_CHECKING:
    from discord import MessageReference


reserved_words = ['edit', 'add', 'create', 'info', 'delete', 'list', 'text', 'name', 'remove', 'ban']


async def tag_work(ctx, tag_name):
    with db.session_scope() as ses:
        tag_row = ses.query(db.tg).filter_by(name=tag_name).first()
        if tag_row:
            tag_row.uses += 1

            def replied_reference(msg: Message) -> Optional[MessageReference]:
                ref = msg.reference  # you might want to put this under Context subclass
                if ref and isinstance(ref.resolved, Message):
                    return ref.resolved.to_reference()
                return None

            reference = replied_reference(ctx.message) or ctx.message
            await ctx.send(content=tag_row.content, reference=reference)
        else:
            em = Embed(colour=Clr.error, description='Sorry! Tag under such name does not exist')
            prefix = getattr(ctx, 'clean_prefix', '/')
            em.set_footer(text=f'Consider making one with `{prefix}tags add`')
            if isinstance(ctx, commands.Context):
                await ctx.reply(embed=em)
            elif isinstance(ctx, Interaction):
                await ctx.response.send_message(embed=em)


class TagTextFlags(commands.FlagConverter, case_insensitive=True):
    tag_name: str
    tag_text: str


class Tags(commands.Cog):
    """
    Use prepared texts to answer repeating questions

    Inspired by programming servers where a lot of questions get repeated daily. \
    So in the end if somebody asks "How to learn Python?" - people just use \
    `$tag learn python` and the bot gives well-prepared, well-detailed answer.
    """
    def __init__(self, bot):
        self.bot = bot
        self.help_emote = Ems.peepoBusiness

    @app_commands.command(
        name='tag',
        description='Use tag for copypaste message'
    )
    @app_commands.describe(tag_name="Summon tag under this name")
    async def tag_slh(self, ntr: Interaction, *, tag_name: str):
        ctx = await Context.from_interaction(ntr)
        await tag_work(ctx, tag_name.lower())

    @commands.hybrid_group(
        name='tags',
        brief=Ems.slash,
        aliases=['tag'],
        invoke_without_command=True
    )
    async def tags(self, ctx: Context, *, tag_name: str):
        """Execute tag frombot database"""
        await tag_work(ctx, tag_name.lower())

    @tags.error
    async def tags_error(self, ctx: Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.scnf()

    @tags.command(
        name='add',
        brief=Ems.slash,
        description='Add a new tag',
        aliases=['create'],
        usage='name: <tag_name> text: <tag_text>'
    )
    @app_commands.describe(tag_name="Enter short name for your tag (<100 symbols)")
    @app_commands.describe(tag_text="Enter content for your tag (<2000 symbols)")
    async def add(self, ctx, *, flags: TagTextFlags):
        """Add a new tag into bot's database. Tag name should be <100 symbols and tag text <2000 symbols"""
        tag_name = flags.tag_name.lower()
        if tag_name.split(' ')[0] in reserved_words:
            embed = Embed(colour=Clr.error)
            embed.description = "Sorry! the first word of your proposed `tag_name` is reserved by system"
        elif len(tag_name) < 3:
            embed = Embed(colour=Clr.error)
            embed.description = "Sorry! `tag_name` should be more than 2 symbols"
        elif len(tag_name) > 100:
            embed = Embed(colour=Clr.error)
            embed.description = "Sorry! `tag_name` should be less than 100 symbols"
        elif len(tag_name) > 2000:
            embed = Embed(colour=Clr.error)
            embed.description = "Sorry! `tag_text` should be less than 2000 symbols"
        else:
            with db.session_scope() as ses:
                user_row = ses.query(db.m).filter_by(id=ctx.author.id).first()
                if not user_row.can_make_tags:
                    embed = Embed(colour=Clr.red)
                    embed.description = 'Sorry! You are banned from making new tags'
                elif ses.query(db.tg).filter_by(name=tag_name).first():
                    embed = Embed(colour=Clr.error)
                    embed.description = 'Sorry! Tag under such name already exists'
                else:
                    db.append_row(
                        db.tg, name=tag_name, content=flags.tag_text, owner_id=ctx.author.id,
                        created_at=datetime.now(timezone.utc)
                    )
                    embed = Embed(colour=Clr.prpl)
                    embed.description = f"Tag under name `{tag_name}` was successfully added"
        return await ctx.reply(embed=embed)

    @add.error
    async def add_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.MissingRequiredFlag):
            ctx.error_handled = True
            em = Embed(colour=Clr.error).set_author(name='WrongCommandUsage')
            em.description = \
                'Sorry! Command usage is\n `$tag add name: <tag_name> text: <tag_text>`\n' \
                'where `<tag_name>` is <100 symbols and `<tag_text>` is <2000 symbols. \n' \
                'Flags `name` and `text` are **required**.'
            await ctx.reply(embed=em)

    @tags.command(
        name='info',
        brief=Ems.slash,
        description='Get info about specific tag'
    )
    @app_commands.describe(tag_name="Tag name")
    async def info(self, ctx, *, tag_name: str):
        tag_name = tag_name.lower()
        with db.session_scope() as ses:
            """Get info about specific tag"""
            tag_row = ses.query(db.tg).filter_by(name=tag_name).first()
            if tag_row:
                em = Embed(colour=Clr.prpl, title='Tag info')
                tag_owner = self.bot.get_user(tag_row.owner_id)
                tag_dt: datetime = tag_row.created_at.replace(tzinfo=timezone.utc)
                em.description = \
                    f'Tag name: `{tag_row.name}`\n' \
                    f'Tag owner: {tag_owner.mention}\n' \
                    f'Tag was used {tag_row.uses} times\n' \
                    f'Tag was created on {format_dt(tag_dt)}'
            else:
                em = Embed(colour=Clr.error)
                em.description = 'Sorry! Tag under such name does not exist'
            await ctx.reply(embed=em)

    @tags.command(
        name='delete',
        brief=Ems.slash,
        description='Delete your tag from bot database',
        aliases=['remove']
    )
    @app_commands.describe(tag_name="Tag name")
    async def delete(self, ctx, *, tag_name: str):
        """Delete tag from bot database"""
        tag_name = tag_name.lower()
        with db.session_scope() as ses:
            tag_query = ses.query(db.tg).filter_by(name=tag_name)
            if tag_row := tag_query.first():
                print(get(ctx.author.roles, id=Rid.discord_mods))
                if ctx.author.id == tag_row.owner_id or get(ctx.author.roles, id=Rid.discord_mods) is not None:
                    tag_query.delete()
                    embed = Embed(colour=Clr.prpl)
                    embed.description = f'Successfully deleted tag under name `{tag_name}`'
                else:
                    embed = Embed(colour=Clr.error)
                    embed.description = \
                        f'Sorry! Only tag owner which is {umntn(tag_row.owner_id)} ' \
                        f'or {rmntn(Rid.discord_mods)} can delete this tag'
            else:
                embed = Embed(colour=Clr.error)
                embed.description = 'Sorry! Tag under such name does not exist'
            await ctx.reply(embed=embed)

    @tags.command(
        name='list',
        brief=Ems.slash,
        description='Get a list of all tags on the guild'
    )
    async def list(self, ctx):
        """Show list of all tags in bot's database"""
        with db.session_scope() as ses:
            em = Embed(colour=Clr.prpl, title='List of tags')
            em.description = ', '.join([f'`{row.name}`' for row in ses.query(db.tg).order_by(db.tg.name)])
            await ctx.reply(embed=em)

    @commands.has_role(Rid.discord_mods)
    @commands.has_permissions(manage_messages=True)
    @app_commands.default_permissions(manage_messages=True)
    @commands.hybrid_group(
        name='modtags',
        aliases=['modtag'],
        invoke_without_command=True
    )
    async def modtags(self, ctx: Context):
        """Group command about ModTags, for actual commands use it together with subcommands"""
        if ctx.invoked_subcommand is None:
            await ctx.scnf()

    @staticmethod
    async def tag_ban_work(ctx, member, mybool):
        with db.session_scope() as ses:
            user_row = ses.query(db.m).filter_by(id=member.id).first()
            user_row.can_make_tags = mybool
        embed = Embed(colour=Clr.red)
        embed.description = f"{member.mention} is now {'un' if mybool else ''}banned from making new tags"
        await ctx.reply(embed=embed)

    @modtags.command(
        name='ban',
        brief=Ems.slash,
        description='Ban member from creating new tags'
    )
    async def ban(self, ctx, member: Member):
        """Ban member from creating new tags"""
        await self.tag_ban_work(ctx, member, False)

    @modtags.command(
        name='unban',
        brief=Ems.slash,
        description='Unban member from creating new tags'
    )
    async def unban(self, ctx, member: Member):
        """Unban member from creating new tags"""
        await self.tag_ban_work(ctx, member, True)


async def setup(bot):
    await bot.add_cog(Tags(bot))
