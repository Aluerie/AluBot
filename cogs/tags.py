from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from utils import AluContext
from utils.const import Colour, Emote, Role

if TYPE_CHECKING:
    from utils import AluBot


reserved_words = ['edit', 'add', 'create', 'info', 'delete', 'list', 'text', 'name', 'remove', 'ban']


class TagTextFlags(commands.FlagConverter, case_insensitive=True):
    name: str
    text: str


class Tags(commands.Cog):
    """Use prepared texts to answer repeating questions

    Inspired by programming servers where a lot of questions get repeated daily. \
    So in the end if somebody asks "How to learn Python?" - people just use \
    `$tag learn python` and the bot gives well-prepared, well-detailed answer.
    """

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Emote.PepoBeliever)

    async def tag_work(self, ctx: AluContext, tag_name: str, *, pool: Optional[asyncpg.Pool] = None):
        pool = pool or self.bot.pool

        query = """ SELECT tags.name, tags.content
                    FROM tags
                    WHERE LOWER(tags.name)=$1;
                """

        row = await pool.fetchrow(query, tag_name)

        if row is None:
            prefix = getattr(ctx, 'clean_prefix', '/')
            e = discord.Embed(description='Sorry! Tag under such name does not exist', colour=Colour.error())
            e.set_footer(text=f'Consider making one with `{prefix}tags add`')
            if isinstance(ctx, commands.Context):
                await ctx.reply(embed=e)
            elif isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(embed=e)
        else:

            def replied_reference(msg: discord.Message) -> Optional[discord.MessageReference]:
                ref = msg.reference  # you might want to put this under Context subclass
                if ref and isinstance(ref.resolved, discord.Message):
                    return ref.resolved.to_reference()
                return None

            reference = replied_reference(ctx.message) or ctx.message
            await ctx.send(content=row.content, reference=reference)

            # update the usage
            query = "UPDATE tags SET uses = uses + 1 WHERE tags.name=$1;"
            await pool.execute(query, row.name)

    @app_commands.command(name='tag', description='Use tag for copypaste message')
    @app_commands.describe(tag_name="Summon tag under this name")
    async def tag_slh(self, ntr: discord.Interaction, *, tag_name: str):
        ctx = await AluContext.from_interaction(ntr)
        await self.tag_work(ctx, tag_name.lower())

    @commands.hybrid_group(name='tags', aliases=['tag'], invoke_without_command=True)
    async def tags(self, ctx: AluContext, *, tag_name: str):
        """Execute tag from the database"""
        await self.tag_work(ctx, tag_name.lower())

    @tags.error
    async def tags_error(self, ctx: AluContext, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.scnf()

    @tags.command(
        name='add', description='Add a new tag', aliases=['create'], usage='name: <tag_name> text: <tag_text>'
    )
    @app_commands.describe(name="Enter short name for your tag (<100 symbols)")
    @app_commands.describe(text="Enter content for your tag (<2000 symbols)")
    async def add(self, ctx, *, flags: TagTextFlags):
        """Add a new tag into bot's database. Tag name should be <100 symbols and tag text <2000 symbols"""
        tag_name = flags.name.lower()
        if tag_name.split(' ')[0] in reserved_words:
            raise commands.BadArgument("Sorry! the first word of your proposed `tag_name` is reserved by system")
        elif len(tag_name) < 3:
            raise commands.BadArgument("Sorry! `tag_name` should be more than 2 symbols")
        elif len(tag_name) > 100:
            raise commands.BadArgument("Sorry! `tag_name` should be less than 100 symbols")
        elif len(tag_name) > 2000:
            raise commands.BadArgument("Sorry! `tag_text` should be less than 2000 symbols")
        else:
            query = 'SELECT users.can_make_tags FROM users WHERE users.id=$1;'
            can_make_tags = await self.bot.pool.fetchval(query, ctx.author.id)
            if not can_make_tags:
                raise commands.BadArgument('Sorry! You are banned from making new tags')
            else:
                query = 'SELECT tags.name FROM tags WHERE tags.name=$1;'
                tag_exists = await self.bot.pool.fetchval(query, tag_name)
                if tag_exists:
                    raise commands.BadArgument('Sorry! Tag under such name already exists')
                else:
                    query = "INSERT INTO tags (name, owner_id, content) VALUES ($1, $2, $3);"
                    await self.bot.pool.execute(query, tag_name, ctx.author.id, flags.text)
                    e = discord.Embed(colour=Colour.prpl())
                    e.description = f"Tag under name `{tag_name}` was successfully added"
        return await ctx.reply(embed=e)

    @add.error
    async def add_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.MissingRequiredFlag):
            ctx.error_handled = True
            e = discord.Embed(colour=Colour.error()).set_author(name='WrongCommandUsage')
            e.description = (
                'Sorry! Command usage is\n `$tag add name: <tag_name> text: <tag_text>`\n'
                'where `<tag_name>` is <100 symbols and `<tag_text>` is <2000 symbols. \n'
                'Flags `name` and `text` are **required**.'
            )
            await ctx.reply(embed=e)

    @tags.command(name='info', description='Get info about specific tag')
    @app_commands.describe(tag_name="Tag name")
    async def info(self, ctx: AluContext, *, tag_name: str):
        """Get info about the specific tag."""
        tag_name = tag_name.lower()
        query = 'SELECT * FROM tags WHERE name=$1'
        row = await self.bot.pool.fetchrow(query, tag_name)
        if row:
            e = discord.Embed(colour=Colour.prpl(), title='Tag info')
            tag_owner = self.bot.get_user(row.owner_id)
            e.description = (
                f"Tag name: `{row.name}`\n"
                f"Tag owner: {tag_owner.mention}\n"
                f"Tag was used {row.uses} times\n"
                f"Tag was created on {discord.utils.format_dt(row.created_at)}"
            )
        else:
            e = discord.Embed(description='Sorry! Tag under such name does not exist', colour=Colour.error())
        await ctx.reply(embed=e)

    @tags.command(name='delete', description='Delete your tag from bot database', aliases=['remove'])
    @app_commands.describe(tag_name="Tag name")
    async def delete(self, ctx: AluContext, *, tag_name: str):
        """Delete tag from bot database"""
        tag_name = tag_name.lower()

        bypass_owner_check = ctx.author.id == self.bot.owner_id or ctx.author.guild_permissions.manage_messages
        clause = 'tags.name=$1'
        if bypass_owner_check:
            args = [tag_name]
        else:
            args = [tag_name, ctx.author.id]
            clause = f'{clause} and owner_id=$2'

        query = f'DELETE FROM tags WHERE {clause} RETURNING name;'
        val = await self.bot.pool.fetchrow(query, *args)

        if val:
            e = discord.Embed(colour=Colour.prpl())
            e.description = f'Successfully deleted tag under name `{tag_name}`'
        else:
            e = discord.Embed(colour=Colour.error())
            e.description = (
                f'Sorry! Either the tag with such name does not exist or '
                f'you do not have permissions to perform this action.'
            )
        await ctx.reply(embed=e)

    @tags.command(name='list', description='Get a list of all tags on the guild')
    async def list(self, ctx):
        """Show list of all tags in bot's database"""
        query = "SELECT name FROM tags;"
        rows = await self.bot.pool.fetch(query)
        e = discord.Embed(title='List of tags', colour=Colour.prpl())
        e.description = ', '.join([f"`{row.name}`" for row in rows])
        await ctx.reply(embed=e)

    @commands.has_role(Role.discord_mods)
    @commands.has_permissions(manage_messages=True)
    @app_commands.default_permissions(manage_messages=True)
    @commands.hybrid_group(name='modtags', aliases=['modtag'], invoke_without_command=True)
    async def modtags(self, ctx: AluContext):
        """Group command about ModTags, for actual commands use it together with subcommands"""
        if ctx.invoked_subcommand is None:
            await ctx.scnf()

    async def tag_ban_work(self, ctx, member: discord.Member, mybool):
        query = 'UPDATE users SET can_make_tags=$1 WHERE users.id=$2;'
        await self.bot.pool.execute(query, mybool, member.id)

        e = discord.Embed(colour=Colour.red())
        e.description = f"{member.mention} is now {'un' if mybool else ''}banned from making new tags"
        await ctx.reply(embed=e)

    @modtags.command(name='ban', description='Ban member from creating new tags')
    async def ban(self, ctx: AluContext, member: discord.Member):
        """Ban member from creating new tags"""
        await self.tag_ban_work(ctx, member, False)

    @modtags.command(name='unban', description='Unban member from creating new tags')
    async def unban(self, ctx, member: discord.Member):
        """Unban member from creating new tags"""
        await self.tag_ban_work(ctx, member, True)


async def setup(bot: AluBot):
    await bot.add_cog(Tags(bot))
