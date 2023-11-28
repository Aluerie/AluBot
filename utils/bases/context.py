from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, Callable, Generic, Optional, Sequence, TypeVar, Union, overload

import discord
from discord.ext import commands

from ..const import Colour, Tick

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from asyncpg import Pool

    from bot import AluBot
T = TypeVar("T")
__all__ = ("AluContext", "AluGuildContext", "ConfirmationView")


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
            e.description = "Sorry! This confirmation dialog is not for you."
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

    @discord.ui.button(emoji=Tick.yes, label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, ntr: discord.Interaction, _: discord.ui.Button):
        await self.button_callback(ntr, True)

    @discord.ui.button(emoji=Tick.no, label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, ntr: discord.Interaction, _: discord.ui.Button):
        await self.button_callback(ntr, False)


class DisambiguatorView(discord.ui.View, Generic[T]):
    message: discord.Message
    selected: T

    def __init__(self, ctx: AluContext, data: list[T], entry: Callable[[T], Any]):
        super().__init__()
        self.ctx: AluContext = ctx
        self.data: list[T] = data

        options = []
        for i, x in enumerate(data):
            opt = entry(x)
            if not isinstance(opt, discord.SelectOption):
                opt = discord.SelectOption(label=str(opt))
            opt.value = str(i)
            options.append(opt)

        select = discord.ui.Select(options=options)

        select.callback = self.on_select_submit
        self.select = select
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This select menu is not meant for you, sorry.", ephemeral=True)
            return False
        return True

    async def on_select_submit(self, interaction: discord.Interaction):
        index = int(self.select.values[0])
        self.selected = self.data[index]
        await interaction.response.defer()
        if not self.message.flags.ephemeral:
            await self.message.delete()

        self.stop()


class AluContext(commands.Context):
    """The subclassed Context to allow some extra functionality."""

    if TYPE_CHECKING:
        bot: AluBot

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pool: Pool = self.bot.pool
        self.is_error_handled: bool = False

    def __repr__(self) -> str:
        return f"<AluContext cmd={self.command} ntr={self.tick(bool(self.interaction))} author={self.author}>"

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

    async def disambiguate(self, matches: list[T], entry: Callable[[T], Any], *, ephemeral: bool = False) -> T:
        if len(matches) == 0:
            raise ValueError("No results found.")

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 25:
            raise ValueError("Too many results... sorry.")

        view = DisambiguatorView(self, matches, entry)
        view.message = await self.send(
            "There are too many matches... Which one did you mean?", view=view, ephemeral=ephemeral
        )
        await view.wait()
        return view.selected

    @staticmethod
    def tick(semi_bool: bool | None) -> str:
        match semi_bool:
            case True:
                return Tick.yes
            case False:
                return Tick.no
            case _:
                return Tick.black

    async def tick_reaction(self, semi_bool: bool | None):
        with contextlib.suppress(discord.HTTPException):
            await self.message.add_reaction(self.tick(semi_bool))

    @discord.utils.cached_property
    def replied_reference(self) -> Optional[discord.MessageReference]:
        """Used to redirect reference to `ctx.message`'s reference."""
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference(fail_if_not_exists=False)  # maybe don't make it default
        return None

    @discord.utils.cached_property
    def replied_message(self) -> Optional[discord.Message]:
        """Used to get message from provided reference in `ctx.message`"""
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved
        return None

    # Just a copy of overloads from `super().reply`
    # If discord.py changes signature of `ctx.reply` - you gotta recopy these overloads as well
    # the entire purpose of this is to have `fail_if_not_exists=False` in my reply as a default behavior

    @overload
    async def reply(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embed: discord.Embed = ...,
        file: discord.File = ...,
        stickers: Sequence[Union[discord.GuildSticker, discord.StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: discord.AllowedMentions = ...,
        reference: Union[discord.Message, discord.MessageReference, discord.PartialMessage] = ...,
        mention_author: bool = ...,
        view: discord.ui.View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
    ) -> discord.Message:
        ...

    @overload
    async def reply(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embed: discord.Embed = ...,
        files: Sequence[discord.File] = ...,
        stickers: Sequence[Union[discord.GuildSticker, discord.StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: discord.AllowedMentions = ...,
        reference: Union[discord.Message, discord.MessageReference, discord.PartialMessage] = ...,
        mention_author: bool = ...,
        view: discord.ui.View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
    ) -> discord.Message:
        ...

    @overload
    async def reply(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embeds: Sequence[discord.Embed] = ...,
        file: discord.File = ...,
        stickers: Sequence[Union[discord.GuildSticker, discord.StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: discord.AllowedMentions = ...,
        reference: Union[discord.Message, discord.MessageReference, discord.PartialMessage] = ...,
        mention_author: bool = ...,
        view: discord.ui.View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
    ) -> discord.Message:
        ...

    @overload
    async def reply(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        embeds: Sequence[discord.Embed] = ...,
        files: Sequence[discord.File] = ...,
        stickers: Sequence[Union[discord.GuildSticker, discord.StickerItem]] = ...,
        delete_after: float = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: discord.AllowedMentions = ...,
        reference: Union[discord.Message, discord.MessageReference, discord.PartialMessage] = ...,
        mention_author: bool = ...,
        view: discord.ui.View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
    ) -> discord.Message:
        ...

    # Literal copy of .reply from the library but with `.to_reference(fail_if_not_exists=False)`
    @discord.utils.copy_doc(commands.Context.reply)
    async def reply(self, content: Optional[str] = None, **kwargs: Any):
        if self.interaction is None:
            return await super().send(content, reference=self.message.to_reference(fail_if_not_exists=False), **kwargs)
        else:
            return await super().send(content, **kwargs)


class AluGuildContext(AluContext):
    if TYPE_CHECKING:
        author: discord.Member
        guild: discord.Guild
        channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread]
        me: discord.Member
