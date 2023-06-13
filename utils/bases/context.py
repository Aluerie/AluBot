from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union, Any

import discord
from discord.ext import commands

from ..const import Colour, Tick

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from asyncpg import Pool

    from ..bot import AluBot

__all__ = (
    'AluContext',
    'AluGuildContext',
)


class ConfirmationView(discord.ui.View):
    def __init__(self, *, timeout: float, author_id: int, delete_after: bool) -> None:
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.delete_after: bool = delete_after
        self.author_id: int = author_id
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, ntr: discord.Interaction) -> bool:
        if ntr.user and ntr.user.id == self.author_id:
            return True
        else:
            e = discord.Embed(colour=Colour.error())
            e.description = 'Sorry! This confirmation dialog is not for you.'
            await ntr.response.send_message(embed=e, ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        if self.delete_after and self.message:
            await self.message.delete()

    async def button_callback(self, ntr: discord.Interaction, yes_no: bool):
        self.value = yes_no
        await ntr.response.defer()
        if self.delete_after:
            await ntr.delete_original_response()
        else:
            for item in self.children:
                item.disabled = True  # type: ignore
            await ntr.edit_original_response(view=self)
        self.stop()

    @discord.ui.button(emoji=Tick.yes, label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, ntr: discord.Interaction, _: discord.ui.Button):
        await self.button_callback(ntr, True)

    @discord.ui.button(emoji=Tick.no, label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, ntr: discord.Interaction, _: discord.ui.Button):
        await self.button_callback(ntr, False)


class AluContext(commands.Context):
    """The subclassed Context to allow some extra functionality."""

    if TYPE_CHECKING:
        bot: AluBot

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pool: Pool = self.bot.pool
        self.is_error_handled: bool = False

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
        content: str = discord.utils.MISSING,
        embed: discord.Embed = discord.utils.MISSING,
        timeout: float = 100.0,
        delete_after: bool = True,
        author_id: Optional[int] = None,
    ) -> Optional[bool]:
        """A shortcut to prompt function from bot class."""
        return await self.bot.prompt(
            self,
            content=content,
            embed=embed,
            timeout=timeout,
            delete_after=delete_after,
            author_id=author_id,
        )

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

            e = discord.Embed(colour=Colour.error(), description=ans)
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
    
    # async def reply(self, content: Optional[str] = None, *, fail_if_not_exists: bool = True, **kwargs: Any):
    #     reference = kwargs.get('reference') or self.message.to_reference(fail_if_not_exists=fail_if_not_exists)
    #     await super().reply(content, reference=reference, **kwargs)


class AluGuildContext(AluContext):
    if TYPE_CHECKING:
        author: discord.Member
        guild: discord.Guild
        channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread]
        me: discord.Member
