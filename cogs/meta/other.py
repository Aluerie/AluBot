from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Literal, Tuple

import unicodedata

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_owner
from utils.context import Context
from utils.var import Cid, Clr, Lmt

from ._base import MetaBase

if TYPE_CHECKING:
    pass


class FeedbackModal(discord.ui.Modal, title='Submit Feedback'):
    summary = discord.ui.TextInput(
        label='Summary',
        placeholder='A brief explanation of what you want',
        max_length=Lmt.Embed.title
    )
    details = discord.ui.TextInput(
        label='Details',
        placeholder='Leave a comment',
        style=discord.TextStyle.long,
        required=False
    )

    def __init__(self, cog: OtherCog) -> None:
        super().__init__()
        self.cog: OtherCog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = self.cog.feedback_channel
        if channel is None:
            await interaction.response.send_message('Sorry, something went wrong \N{THINKING FACE}', ephemeral=True)
            return

        e = self.cog.get_feedback_embed(interaction, summary=str(self.summary), details=self.details.value)
        await channel.send(embed=e)
        e2 = discord.Embed(colour=Clr.prpl, description='Successfully submitted feedback')
        await interaction.response.send_message(embed=e2, ephemeral=True)


class OtherCog(MetaBase):

    # **The** famous Umbra\'s sync command holy moly. `?tag usc`. Or `?tag umbra sync command`
    @is_owner()
    @commands.command()
    async def sync(
            self,
            ctx: Context,
            guilds: commands.Greedy[discord.Object],
            spec: Optional[Literal["~", "*", "^"]] = None
    ) -> None:
        """Sync command. Usage examples:
        * `$sync` -> global sync
        * `$sync ~` -> sync current guild
        * `$sync *` -> copies all global app commands to current guild and syncs
        * `$sync ^` -> clears all commands from the current guild target and syncs (removes guild commands)
        * `$sync id_1 id_2` -> syncs guilds with id 1 and 2
        """

        # todo: remove this from help for plebs
        if not guilds:
            match spec:
                case "~":
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                case "*":
                    ctx.bot.tree.copy_global_to(guild=ctx.guild)
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                case "^":
                    ctx.bot.tree.clear_commands(guild=ctx.guild)
                    await ctx.bot.tree.sync(guild=ctx.guild)
                    synced = []
                case _:
                    synced = await ctx.bot.tree.sync()

            e = discord.Embed(colour=Clr.prpl)
            e.description = f"Synced `{len(synced)}` commands {'globally' if spec is None else 'to the current guild.'}"
            await ctx.reply(embed=e)
            return

        fmt = 0
        cmds = []
        for guild in guilds:
            try:
                cmds += await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                fmt += 1
        e = discord.Embed(colour=Clr.prpl)
        e.description = f"Synced the tree to `{fmt}/{len(guilds)}` guilds."
        await ctx.reply(embed=e)

    @commands.command(aliases=['join'])
    async def invite(self, ctx: Context):
        """Show the invite link, so you can add me to your server.
        You can also press "Add to Server" button in my profile.
        """
        perms = discord.Permissions.all()
        # perms.read_messages = True
        url = discord.utils.oauth_url(self.bot.client_id, permissions=perms)
        e = discord.Embed(title='Invite link for the bot', url=url, description=url, color=Clr.prpl)
        e.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=e)

    @property
    def feedback_channel(self) -> Optional[discord.TextChannel]:
        return self.bot.get_channel(Cid.global_logs)  # type: ignore

    @staticmethod
    def get_feedback_embed(
        ctx_ntr: Context | discord.Interaction,
        *,
        summary: Optional[str] = None,
        details: Optional[str] = None,
    ) -> discord.Embed:
        e = discord.Embed(title=summary, description=details, colour=Clr.prpl)

        if ctx_ntr.guild is not None:
            e.add_field(name='Server', value=f'{ctx_ntr.guild.name} | ID: {ctx_ntr.guild.id}', inline=False)

        if ctx_ntr.channel is not None:
            e.add_field(name='Channel', value=f'#{ctx_ntr.channel} | ID: {ctx_ntr.channel.id}', inline=False)

        if isinstance(ctx_ntr, discord.Interaction):
            e.timestamp, user = ctx_ntr.created_at, ctx_ntr.user
        else:
            e.timestamp, user = ctx_ntr.message.created_at, ctx_ntr.author
        e.set_author(name=str(user), icon_url=user.display_avatar.url)
        e.set_footer(text=f'Author ID: {user.id}')
        return e

    @commands.command(name='feedback')
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def text_feedback(self, ctx: Context, *, details: str):
        """Give feedback about the bot directly to the bot developer.
        This is a quick way to request features or bug fixes. \
        The bot will DM you about the status of your request if possible/needed.
        You can also open issues/PR on [GitHub](https://github.com/Aluerie/AluBot).
        """

        channel = self.feedback_channel
        if channel is None:
            return

        e = self.get_feedback_embed(ctx, details=details)
        await channel.send(embed=e)
        e2 = discord.Embed(colour=Clr.prpl, description='Successfully sent feedback')
        await ctx.send(embed=e2)

    @app_commands.command(name='feedback')
    async def slash_feedback(self, ntr: discord.Interaction):
        """Give feedback about the bot directly to the bot developer."""
        await ntr.response.send_modal(FeedbackModal(self))

    @is_owner()
    @commands.command(aliases=['pm'], hidden=True)
    async def dm(self, ctx: Context, user: discord.User, *, content: str):
        e = discord.Embed(colour=Clr.prpl, title='Message from a developer')
        e.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        e.description = content
        e.set_footer(
            text=(
                'This message is sent to you in DMs because you had previously submitted feedback or '
                'I found a bug in a command you used, I do not monitor this DM. '
                '\n'
                'Please, use `/feedback` if you *need* to answer my message.'
            )
        )
        await user.send(embed=e)
        e2 = discord.Embed(colour=Clr.prpl, description='DM successfully sent.')
        await ctx.send(embed=e2)

    @commands.command()
    async def charinfo(self, ctx: Context, *, characters: str):
        """Shows information about a character(-s). \
        Only up to a few characters tho.
        """
        # todo: move this to tools or smth
        def to_string(c: str) -> Tuple[str, str]:
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, None)
            name = f'\N{BLACK CIRCLE} `\\N{{{name}}}`' if name else 'Name not found.'
            string = f'[`\\U{digit:>08}`](https://www.fileformat.info/info/unicode/char/{digit}) `{c}`'
            return name, string

        e = discord.Embed(colour=discord.Colour.blurple())
        for c in characters[:10]:
            n, s = to_string(c)
            e.add_field(name=n, value=s, inline=False)
        if len(characters) > 10:
            e.colour = Clr.error
            e.set_footer(text='Output was too long. Displaying only first 10 chars.')

        await ctx.send(embed=e)
