# todo: move this file somewhere else - some guild setup material, maybe just one general cog for setup command
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from typing_extensions import Self

import discord
from discord.ext import commands

from utils import checks
from utils.var import Clr

from ._base import MetaBase
from .setup import SetupPages, SetupCog

if TYPE_CHECKING:
    from utils.bot import AluBot
    from utils.context import GuildContext


class PrefixSetModal(discord.ui.Modal, title='New prefix setup'):

    prefix = discord.ui.TextInput(
        label='New prefix for the server', placeholder='Enter up to 3 character', max_length=3
    )

    def __init__(self, cog: PrefixSetupCog, paginator: SetupPages) -> None:
        super().__init__()
        self.cog: PrefixSetupCog = cog
        self.paginator: SetupPages = paginator

    async def on_error(self, ntr: discord.Interaction, error: Exception, /) -> None:
        e = discord.Embed(colour=Clr.error)
        if isinstance(error, commands.BadArgument):
            e.description = f'{error}'
        else:
            e.description = 'Unknown error, sorry'
        await ntr.response.send_message(embed=e, ephemeral=True)

    async def on_submit(self, ntr: discord.Interaction[AluBot]) -> None:
        p: GuildPrefix = await GuildPrefix.construct(ntr.client, ntr.guild, str(self.prefix.value))
        e = await p.set_prefix()
        await ntr.response.send_message(embed=e, ephemeral=True)
        await self.paginator.show_page(ntr, self.paginator.current_page_number)


class PrefixSetupView(discord.ui.View):
    def __init__(self, cog: PrefixSetupCog, paginator: SetupPages) -> None:
        super().__init__()
        self.cog: PrefixSetupCog = cog
        self.paginator: SetupPages = paginator

    @discord.ui.button(emoji='\N{HEAVY DOLLAR SIGN}', label='Change prefix', style=discord.ButtonStyle.blurple)
    async def set_prefix(self, ntr: discord.Interaction[AluBot], _btn: discord.ui.Button):
        await ntr.response.send_modal(PrefixSetModal(self.cog, self.paginator))

    @discord.ui.button(emoji='\N{BANKNOTE WITH DOLLAR SIGN}', label='Reset prefix', style=discord.ButtonStyle.blurple)
    async def reset_prefix(self, ntr: discord.Interaction[AluBot], _btn: discord.ui.Button):
        p = GuildPrefix(ntr.client, ntr.guild)
        e = await p.set_prefix()
        await ntr.response.send_message(embed=e, ephemeral=True)
        await self.paginator.show_page(ntr, self.paginator.current_page_number)


class GuildPrefix:
    def __init__(self, bot: AluBot, guild: discord.Guild, prefix: Optional[str] = None):
        self.bot: AluBot = bot
        self.guild: discord.Guild = guild
        self.prefix: str = prefix if prefix else bot.main_prefix  # reset zone

    @classmethod
    async def from_guild(cls, bot: AluBot, guild: discord.Guild) -> Self:
        prefix = bot.prefixes.get(guild.id)
        if prefix is None:
            prefix = bot.main_prefix
        return cls(bot, guild, prefix)

    def check_prefix(self) -> discord.Embed:
        e = discord.Embed(colour=Clr.rspbrry)
        e.description = f'Current prefix: `{self.prefix}`'
        return e

    @classmethod
    async def construct(cls, bot: AluBot, guild: discord.Guild, new_prefix: str) -> Self:
        bot_user_id = bot.user.id
        # Since I want to allow people to set prefixes with SetupView -
        # I guess I have to do these quirks to be able to check prefix both in Interactions and from Converters
        # Eh, probably we should not restrict people much, but eh let's do it for fun logic reasons.
        # Anyway, now let's verify Prefix
        if new_prefix.startswith((f'<@{bot_user_id}>', f'<@!{bot_user_id}>')):
            # Just to remind the user that it is a thing, even tho modal doesn't allow >3 characters;
            raise commands.BadArgument('That is a reserved prefix already in use.')
        if len(new_prefix.split()) > 1:
            raise commands.BadArgument('Space usage is not allowed in `prefix set` command')
        if (le := len(new_prefix)) > 3:
            raise commands.BadArgument(f'Prefix should consist of 1, 2 or 3 characters. Not {le} !')
        return cls(bot, guild, new_prefix)

    @classmethod
    async def convert(cls, ctx: GuildContext, new_prefix: str) -> Self:
        return await cls.construct(ctx.bot, ctx.guild, new_prefix)

    async def set_prefix(self) -> discord.Embed:
        guild_id, new_prefix = self.guild.id, self.prefix
        e = discord.Embed(colour=Clr.prpl)
        if self.prefix == self.bot.main_prefix:
            if not self.bot.prefixes.get(guild_id):
                e.description = f'The prefix was already our default `{new_prefix}` sign'
            else:
                await self.bot.prefixes.remove(guild_id)
                e.description = f'Successfully reset prefix to our default `{new_prefix}` sign'
        else:
            await self.bot.prefixes.put(guild_id, new_prefix)
            e.description = f'Changed this server prefix to `{new_prefix}`'
        return e


class PrefixSetupCog(MetaBase, SetupCog, name='Prefix Setup'):
    @property
    def setup_emote(self):
        return '\N{HEAVY DOLLAR SIGN}'

    async def setup_info(self):
        e = discord.Embed(colour=Clr.prpl)
        e.title = 'Server Prefix Setup'
        e.description = (
            'You can choose server prefix with button "Change prefix" below. \n\n'
            f'Bot\'s default prefix for text commands is `{self.bot.main_prefix}`.\n'
            f'The bot also always answers on @-mentions, i.e. {self.bot.user.mention}` help`.'
        )
        return e

    async def setup_state(self, ctx: GuildContext):
        p = await GuildPrefix.from_guild(self.bot, ctx.guild)
        return p.check_prefix()

    async def setup_view(self, pages: SetupPages):
        return PrefixSetupView(self, pages)

    async def prefix_prefix_check_replies(self, ctx: GuildContext):
        p = await GuildPrefix.from_guild(self.bot, ctx.guild)
        e = p.check_prefix()
        e.set_footer(text=f'To change prefix use `@{self.bot.user.name} prefix set` command')
        await ctx.reply(embed=e)

    @checks.is_manager()
    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx: GuildContext):
        """Group command about prefix for this server."""
        await self.prefix_prefix_check_replies(ctx)

    @checks.is_manager()
    @prefix.command(name='check')
    async def prefix_check(self, ctx: GuildContext):
        """Check prefix for this server."""
        await self.prefix_prefix_check_replies(ctx)

    @checks.is_manager()
    @prefix.command(name='set')
    async def prefix_set(self, ctx: GuildContext, *, new_prefix: GuildPrefix):
        """Set new prefix for the server.
        If you have troubles to set a new prefix because other bots also answer it then \
        just mention the bot with the command <@713124699663499274>` prefix set`.
        Spaces are not allowed in the prefix, and it should be 1-3 symbols.
        """

        e = new_prefix.set_prefix()
        await ctx.reply(embed=e)
