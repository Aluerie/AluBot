from discord import Embed, Member, Message, MessageReference, option, default_permissions
from discord.commands import SlashCommandGroup
from discord.ext import commands
from discord.utils import format_dt, get

from utils import database as db
from utils.dcordtools import scnf
from utils.var import *

from datetime import datetime, timezone
from typing import Optional

reserved_words = ['edit', 'add', 'create', 'info', 'delete', 'list', 'text', 'name', 'remove', 'ban']


class TagName(commands.Converter, str):
    async def convert(self, ctx, argument) -> str:
        return argument.lower()


async def tag_work(ctx, tag_name):
    with db.session_scope() as ses:
        tag_row = ses.query(db.tg).filter_by(name=tag_name).first()
        if tag_row:
            tag_row.uses += 1

            def replied_reference(msg: Message) -> Optional[MessageReference]:
                ref = msg.reference  # you might want to put this under Context subclass like Danny
                if ref and isinstance(ref.resolved, Message):
                    return ref.resolved.to_reference()
                return None

            if isinstance(ctx, commands.Context) and (rf := replied_reference(ctx.message)):
                await ctx.send(content=tag_row.content, reference=rf)
            else:
                await ctx.respond(content=tag_row.content)
        else:
            embed = Embed(colour=Clr.error)
            embed.description = 'Sorry! Tag under such name does not exist'
            prefix = getattr(ctx, 'clean_prefix', '/')
            embed.set_footer(text=f'Consider making one with `{prefix}tags add`')
            await ctx.respond(embed=embed)


async def tag_list_work(ctx):
    with db.session_scope() as ses:
        embed = Embed(colour=Clr.prpl, title='List of tags')
        embed.description = ', '.join([f'`{row.name}`' for row in ses.query(db.tg).order_by(db.tg.name)])
        await ctx.respond(embed=embed)


async def tag_delete_work(ctx, tag_name):
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
        await ctx.respond(embed=embed)


async def tag_add_work(ctx, tag_name, tag_txt):
    if tag_name.split(' ')[0] in reserved_words:
        embed = Embed(colour=Clr.error)
        embed.description = "Sorry! the first word of your proposed `tag_name` is reserved by system"
    elif len(tag_name) < 3:
        embed = Embed(colour=Clr.error)
        embed.description = "Sorry! `tag_name` should be more than 2 symbols"
    elif len(tag_name) > 100:
        embed = Embed(colour=Clr.error)
        embed.description = "Sorry! `tag_name` should be less than 100 symbols"
    elif len(tag_txt) > 2000:
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
                    db.tg, name=tag_name, content=tag_txt, owner_id=ctx.author.id, created_at=datetime.now(timezone.utc)
                )
                embed = Embed(colour=Clr.prpl)
                embed.description = f"Tag under name `{tag_name}` was successfully added"
    return await ctx.respond(embed=embed)


class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Tools'

    @commands.slash_command(
        name='tag',
        description='Use tag for copypaste message'
    )
    @option('tag_name', description="Summon tag under this name")
    async def tagslash(self, ctx, *, tag_name: TagName):
        await tag_work(ctx, tag_name)

    tagslash_gr = SlashCommandGroup('tags', 'Commands for managing tags')

    @commands.group(name='tags', brief=Ems.slash, aliases=['tag'], invoke_without_command=True)
    async def tagtext_gr(self, ctx: commands.Context, *, tag_name: TagName):
        """Execute tag frombot database"""
        await tag_work(ctx, tag_name)

    @tagtext_gr.error
    async def tagtext_gr_handle(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await scnf(ctx)

    @tagslash_gr.command(
        name='add',
        description='Add a new tag'
    )
    @option('tag_name', description="Enter short name for your tag (<100 symbols)")
    @option('tag_text', description="Enter content for your tag (<2000 symbols)")
    async def tag_add_slash(self, ctx, tag_name: TagName, *, tag_text: str):
        await tag_add_work(ctx, tag_name, tag_text)

    class TagTextFlags(commands.FlagConverter, case_insensitive=True):
        name: str
        text: str

    @tagtext_gr.command(name='add', brief=Ems.slash, aliases=['create'], usage='name: <tag_name> text: <tag_text>')
    async def tag_add_text(self, ctx, *, flags: TagTextFlags):
        """Add a new tag into bot's database. Tag name should be <100 symbols and tag text <2000 symbols"""
        await tag_add_work(ctx, flags.name, flags.text)

    @tag_add_text.error
    async def tag_add_text_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.MissingRequiredFlag):
            ctx.error_handled = True
            embed = Embed(colour=Clr.error)
            embed.set_author(name='WrongCommandUsage')
            embed.description = \
                'Sorry! Command usage is\n `$tag add name: <tag_name> text: <tag_text>`\n' \
                'where `<tag_name>` is <100 symbols and `<tag_text>` is <2000 symbols. \n' \
                'Flags `name` and `text` are **required**.'
            await ctx.send(embed=embed)

    async def tag_info_work(self, ctx, tag_name):
        with db.session_scope() as ses:
            tag_row = ses.query(db.tg).filter_by(name=tag_name).first()
            if tag_row:
                embed = Embed(colour=Clr.prpl)
                embed.title = 'Tag info'
                tag_owner = self.bot.get_user(tag_row.owner_id)
                tag_dt: datetime = tag_row.created_at.replace(tzinfo=timezone.utc)
                embed.description = \
                    f'Tag name: `{tag_row.name}`\n'\
                    f'Tag owner: {tag_owner.mention}\n' \
                    f'Tag was used {tag_row.uses} times\n' \
                    f'Tag was created on {format_dt(tag_dt)}'
            else:
                embed = Embed(colour=Clr.error)
                embed.description = 'Sorry! Tag under such name does not exist'
            await ctx.respond(embed=embed)

    @tagslash_gr.command(
        name='info',
        description='Get info about specific tag'
    )
    @option('tag_name', description="Tag name")
    async def tag_info_slash(self, ctx, *, tag_name: str):
        await self.tag_info_work(ctx, tag_name)

    @tagtext_gr.command(name='info', brief=Ems.slash)
    async def tag_info_text(self, ctx, *, tag_name: str):
        """Get info about specific tag"""
        await self.tag_info_work(ctx, tag_name)

    @tagslash_gr.command(
        name='delete',
        description='Delete your tag from bot database'
    )
    @option('tag_name', description="Tag name")
    async def tag_delete_slash(self, ctx, *, tag_name: str):
        await tag_delete_work(ctx, tag_name)

    @tagtext_gr.command(name='delete', brief=Ems.slash, aliases=['remove'])
    async def tag_delete_text(self, ctx, *, tag_name: str):
        """Delete tag from bot database"""
        await tag_delete_work(ctx, tag_name)

    @tagslash_gr.command(
        name='list',
        description='Get a list of all tags on the server'
    )
    async def tag_list_slash(self, ctx):
        await tag_list_work(ctx)

    @tagtext_gr.command(name='list', brief=Ems.slash)
    async def tag_list_text(self, ctx):
        """Delete tag from bot database"""
        await tag_list_work(ctx)


async def tag_ban_work(ctx, member, mybool):
    with db.session_scope() as ses:
        user_row = ses.query(db.m).filter_by(id=member.id).first()
        user_row.can_make_tags = mybool
    embed = Embed(colour=Clr.red)
    embed.description = f"{member.mention} is now {'un' if mybool else ''}banned from making new tags"
    await ctx.respond(embed=embed)


class TagsMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Mute'

    tmslh_gr = SlashCommandGroup('tagsmod', 'Commands for moderating tags')

    @commands.group(name='tagsmod', aliases=['tagmod'], invoke_without_command=True)
    async def tmtxt_gr(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await scnf(ctx)

    @commands.has_permissions(manage_messages=True)
    @commands.has_role(Rid.discord_mods)
    @tmtxt_gr.command(name='ban', brief=Ems.slash)
    async def tag_ban_text(self, ctx, member: Member):
        """Ban member from creating new tags"""
        await tag_ban_work(ctx, member, False)

    @default_permissions(manage_messages=True)
    @commands.has_role(Rid.discord_mods)
    @tmslh_gr.command(
        name='ban',
        description='Ban member from creating new tags'
    )
    async def tag_ban_slh(self, ctx, member: Member):
        await tag_ban_work(ctx, member, False)

    @commands.has_permissions(manage_messages=True)
    @commands.has_role(Rid.discord_mods)
    @tmtxt_gr.command(name='unban', brief=Ems.slash)
    async def tag_unban_text(self, ctx, member: Member):
        """Unban member from creating new tags"""
        await tag_ban_work(ctx, member, True)

    @default_permissions(manage_messages=True)
    @commands.has_role(Rid.discord_mods)
    @tmslh_gr.command(
        name='unban',
        description='Unban member from creating new tags'
    )
    async def tag_unban_slh(self, ctx, member: Member):
        await tag_ban_work(ctx, member, True)


def setup(bot):
    bot.add_cog(Tags(bot))
    bot.add_cog(TagsMod(bot))
