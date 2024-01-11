from __future__ import annotations

import contextlib
import datetime
from typing import TYPE_CHECKING, Any, Callable, Generic, Optional, Sequence, TypeVar, Union, overload

import discord
from discord.ext import commands

from utils import formats

from ..const import Colour, Tick

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from asyncpg import Pool

    from bot import AluBot


__all__ = (
    "AluContext",
    "AluGuildContext",
)


class AluContext(commands.Context["AluBot"]):
    """The subclassed Context to allow some extra functionality."""

    if TYPE_CHECKING:
        bot: AluBot

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pool: Pool = self.bot.pool
        self.is_error_handled: bool = False

    def __repr__(self) -> str:
        return f"<AluContext cmd={self.command} ntr={formats.tick(bool(self.interaction))} author={self.author}>"

    # The following attributes are here just to match discord.Interaction properties
    # Just so we don't need to do `if isinstance(discord.Interaction):` checks every time
    # when there is a silly mismatch

    @property
    def client(self) -> AluBot:
        return self.bot

    @property
    def user(self) -> discord.User | discord.Member:
        return self.author

    @property
    def created_at(self) -> datetime.datetime:
        return self.message.created_at

    # Continue

    @property
    def session(self) -> ClientSession:
        return self.bot.session

    async def tick_reaction(self, semi_bool: bool | None):
        with contextlib.suppress(discord.HTTPException):
            await self.message.add_reaction(formats.tick(semi_bool))

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
