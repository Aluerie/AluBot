from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

import discord
from discord.ext import commands

from .var import Clr

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from asyncpg import Pool
    from .bot import AluBot


class ConfirmationView(discord.ui.View):
    def __init__(self, *, timeout: float, author_id: int, ctx: Context, delete_after: bool) -> None:
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.delete_after: Optional[bool] = delete_after
        self.author_id: Optional[int] = author_id
        self.ctx: Optional[Context] = ctx
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, ntr: discord.Interaction) -> bool:
        if ntr.user and ntr.user.id == self.author_id:
            return True
        else:
            e = discord.Embed(description='Sorry! This confirmation dialog is not for you.', colour=Clr.error)
            await ntr.response.send_message(embed=e, ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        if self.delete_after and self.message:
            await self.message.delete()

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, ntr: discord.Interaction, _: discord.ui.Button):
        self.value = True
        await ntr.response.defer()
        if self.delete_after and self.message:
            await self.message.delete()
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, ntr: discord.Interaction, _: discord.ui.Button):
        self.value = False
        await ntr.response.defer()
        if self.delete_after and self.message:
            await self.message.delete()
        self.stop()


class Context(commands.Context):
    bot: AluBot

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool: Pool = self.bot.pool

    # to match interaction
    @property
    def client(self) -> AluBot:
        return self.bot

    # to match interaction
    @property
    def user(self) -> discord.User | discord.Member:
        return self.author

    @property
    def session(self) -> ClientSession:
        return self.bot.session

    async def prompt(
        self,
        *,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        timeout: Optional[float] = 60.0,
        delete_after: Optional[bool] = True,
        author_id: Optional[int] = None,
    ) -> Optional[bool]:
        """
        An interactive reaction confirmation dialog.
        Parameters
        -----------
        content: str
            Text message to show along with the prompt.
        embed:
            Embed to show along with the prompt.
        timeout: float
            How long to wait before returning.
        delete_after: bool
            Whether to delete the confirmation message after we're done.
        author_id: Optional[int]
            The member who should respond to the prompt. Defaults to the author of the
            Context's message.
        Returns
        --------
        Optional[bool]
            ``True`` if explicit confirm,
            ``False`` if explicit deny,
            ``None`` if deny due to timeout
        ----
        """
        if content is None and embed is None:
            raise TypeError('Either content or embed should be provided')

        author_id = author_id or self.author.id
        view = ConfirmationView(timeout=timeout, delete_after=delete_after, ctx=self, author_id=author_id)
        view.message = await self.reply(content=content, embed=embed, view=view)
        await view.wait()
        return view.value

    async def scnf(self):
        if self.invoked_subcommand is None:
            prefix = getattr(self, 'clean_prefix', '/')

            def get_command_signature(command):
                extra_space = '' if command.signature == '' else ' '
                return f'{prefix}{command.qualified_name}{extra_space}{command.signature}'

            ans = 'This command is used only with subcommands. Please, provide one of them:\n'

            # for c in self.command.walk_commands():
            #    print(get_command_signature(c))

            self.command: commands.Group
            for c in self.command.commands:
                if getattr(c, 'commands', None):
                    ans += '\n' + '\n'.join(f'`{get_command_signature(x)}`' for x in c.commands)  # type: ignore
                else:
                    ans += f'\n`{get_command_signature(c)}`'

            e = discord.Embed(colour=Clr.error, description=ans)
            e.set_author(name='SubcommandNotFound')
            e.set_footer(text=f'`{prefix}help {self.command.name}` for more info')
            return await self.reply(embed=e, ephemeral=True)

    async def send_test(self):
        await self.reply('test test')

    @staticmethod
    def tick(semi_bool: bool | None):
        emoji_dict = {True: '\N{WHITE HEAVY CHECK MARK}', False: '\N{CROSS MARK}', None: '\N{BLACK LARGE SQUARE}'}
        return emoji_dict[semi_bool]
        # match semi_bool:
        #     case True:
        #         return '\N{WHITE HEAVY CHECK MARK}'
        #     case False:
        #         return '\N{CROSS MARK}'
        #     case _:
        #         return '\N{BLACK LARGE SQUARE}'

    async def try_tick_reaction(self, semi_bool: bool | None):
        try:
            await self.message.add_reaction(self.tick(semi_bool))
        except:
            pass

    @discord.utils.cached_property
    def replied_reference(self) -> Optional[discord.MessageReference]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    @discord.utils.cached_property
    def replied_message(self) -> Optional[discord.Message]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved
        return None


class GuildContext(Context):
    if TYPE_CHECKING:
        author: discord.Member
        guild: discord.Guild
        channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread]
