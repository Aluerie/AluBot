from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from discord import ButtonStyle, Embed
from discord.ext import commands
from discord.ui import View, button

from utils.var import Clr

if TYPE_CHECKING:
    from utils.bot import VioletBot
    from aiohttp import ClientSession
    from discord import Button, Message, Interaction


class ConfirmationView(View):
    def __init__(self, *, timeout: float, author_id: int, ctx: Context, delete_after: bool) -> None:
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.delete_after: bool = delete_after
        self.author_id: int = author_id
        self.ctx: Context = ctx
        self.message: Optional[Message] = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        else:
            em = Embed(colour=Clr.prpl)
            em.description = 'Sorry! This confirmation dialog is not for you.'
            await interaction.response.send_message(embed=em, ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        if self.delete_after and self.message:
            await self.message.delete()

    @button(label='Confirm', style=ButtonStyle.green)
    async def confirm(self, interaction: Interaction, btn: Button):
        self.value = True
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_message()
        self.stop()

    @button(label='Cancel', style=ButtonStyle.red)
    async def cancel(self, interaction: Interaction, btn: Button):
        self.value = False
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_message()
        self.stop()


class Context(commands.Context):
    bot: VioletBot

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def ses(self) -> ClientSession:
        return self.bot.ses

    async def thinking(self):
        if self.interaction:
            await self.defer()
        else:
            await self.typing()

    async def prompt(
            self,
            *,
            content: str = None,
            embed: Embed = None,
            timeout: float = 60.0,
            delete_after: bool = True,
            author_id: Optional[int] = None,
    ) -> Optional[bool]:
        """An interactive reaction confirmation dialog.
        Parameters
        -----------
        message: str
            The message to show along with the prompt.
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
        view.message = await self.send(content=content, embed=embed, view=view)
        await view.wait()
        return view.value
