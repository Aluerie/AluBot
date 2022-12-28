from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from discord import ButtonStyle, Embed
from discord.ext import commands
from discord.ui import View, button

from .var import Clr

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from asyncpg import Pool
    from discord import (
        Button, Guild, Member, Message, Interaction, TextChannel, Thread, VoiceChannel
    )
    from .bot import AluBot, DatabaseProtocol


class ConfirmationView(View):
    def __init__(self, *, timeout: float, author_id: int, ctx: Context, delete_after: bool) -> None:
        super().__init__(timeout=timeout)
        self.value: Optional[bool]
        self.delete_after: Optional[bool] = delete_after
        self.author_id: Optional[int] = author_id
        self.ctx: Optional[Context] = ctx
        self.message: Optional[Message] = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        else:
            em = Embed(
                colour=Clr.error,
                description='Sorry! This confirmation dialog is not for you.'
            )
            await interaction.response.send_message(embed=em, ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        if self.delete_after and self.message:
            await self.message.delete()

    @button(label='Confirm', style=ButtonStyle.green)  # type: ignore
    async def confirm(self, ntr: Interaction, _: Button):
        self.value = True
        await ntr.response.defer()
        if self.delete_after and self.message:
            await self.message.delete()
        self.stop()

    @button(label='Cancel', style=ButtonStyle.red)  # type: ignore
    async def cancel(self, ntr: Interaction, _: Button):
        self.value = False
        await ntr.response.defer()
        if self.delete_after  and self.message:
            await self.message.delete()
        self.stop()


class Context(commands.Context):
    bot: AluBot

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool: Pool = self.bot.pool

    @property
    def session(self) -> ClientSession:
        return self.bot.session
    
    @property
    def db(self) -> DatabaseProtocol:
        return self.pool  # type: ignore

    async def prompt(
            self,
            *,
            content: str = None,  # type: ignore
            embed: Embed = None,  # type: ignore
            timeout: float = 60.0,
            delete_after: bool = True,
            author_id: Optional[int] = None,
    ) -> Optional[bool]:
        """An interactive reaction confirmation dialog.
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

            em = Embed(colour=Clr.error, description=ans)
            em.set_author(name='SubcommandNotFound')
            em.set_footer(text=f'`{prefix}help {self.command.name}` for more info')
            return await self.reply(embed=em, ephemeral=True)

    async def send_test(self):
        await self.reply('test test')


class GuildContext(Context):
    author: Member
    guild: Guild
    channel: Union[VoiceChannel, TextChannel, Thread]
