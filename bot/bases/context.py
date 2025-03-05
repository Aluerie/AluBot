from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, overload, override

import discord
from discord.ext import commands

from utils import fmt

if TYPE_CHECKING:
    import datetime
    from collections.abc import Sequence

    from aiohttp import ClientSession

    from types_.database import PoolTypedWithAny

    from .. import AluBot


__all__ = (
    "AluContext",
    "AluGuildContext",
    "AluInteraction",
)

# a much shorter alias
type AluInteraction = discord.Interaction[AluBot]


class AluContext(commands.Context["AluBot"]):
    """The subclassed Context to allow some extra functionality."""

    if TYPE_CHECKING:
        bot: AluBot

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pool: PoolTypedWithAny = self.bot.pool
        self.is_error_handled: bool = False

    @override
    def __repr__(self) -> str:
        return (
            f"<AluContext command={self.command} interaction={fmt.tick(bool(self.interaction))} author={self.author}>"
        )

    # The following attributes are here just to match discord.Interaction properties
    # Just so we don't need to do `if isinstance(discord.Interaction):` checks every time
    # when there is a silly mismatch

    @property
    def client(self) -> AluBot:
        """Alias for `ctx.bot` for consistency with `discord.Interaction` (`interaction.client`).

        Example:
        -------
        There are some weird cases we need to compare the type of ctx_ntr to both of them, so instead of doing:
        >>> if isinstance(ctx_ntr, AluContext): #  bot = ctx_ntr.bot
        >>> if isinstance(ctx_ntr, discord.Interaction): #  bot = ctx_ntr.client

        we will just do `ctx_ntr.client` and typechecker is going to be happy.

        """
        return self.bot

    @property
    def user(self) -> discord.User | discord.Member:
        """Alias for `ctx.author` for consistency with `discord.Interaction` (`interaction.user`)."""
        return self.author

    @property
    def created_at(self) -> datetime.datetime:
        """Alias for `ctx.message.created_at` for consistency with `discord.Interaction` (`interaction.created_at`)."""
        return self.message.created_at

    # Continue

    @property
    def session(self) -> ClientSession:
        """Shortcut to `ctx.bot.session`."""
        return self.bot.session

    async def tick_reaction(self, semi_bool: bool | None) -> None:
        """Add tick reaction to `ctx.message`."""
        with contextlib.suppress(discord.HTTPException):
            await self.message.add_reaction(fmt.tick(semi_bool))

    # the next two functions mean the following in a context of discord chat:
    # /--> replying to @Bob: wow, 2+2=5
    # Alice: hey Bob, this is wrong!
    # redirect reference means we are getting "replying to Bob".
    # replied message means we are getting the message object for "wow" Bob's message.

    @discord.utils.cached_property
    def replied_reference(self) -> discord.MessageReference | None:
        """Get redirect reference to `ctx.message`'s reference."""
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference(fail_if_not_exists=False)  # maybe don't make it default
        return None

    @discord.utils.cached_property
    def replied_message(self) -> discord.Message | None:
        """Get message from provided reference in `ctx.message`."""
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
        content: str | None = ...,
        *,
        tts: bool = ...,
        embed: discord.Embed = ...,
        file: discord.File = ...,
        stickers: Sequence[discord.GuildSticker | discord.StickerItem] = ...,
        delete_after: float = ...,
        nonce: str | int = ...,
        allowed_mentions: discord.AllowedMentions = ...,
        reference: discord.Message | discord.MessageReference | discord.PartialMessage = ...,
        mention_author: bool = ...,
        view: discord.ui.View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
    ) -> discord.Message: ...

    @overload
    async def reply(
        self,
        content: str | None = ...,
        *,
        tts: bool = ...,
        embed: discord.Embed = ...,
        files: Sequence[discord.File] = ...,
        stickers: Sequence[discord.GuildSticker | discord.StickerItem] = ...,
        delete_after: float = ...,
        nonce: str | int = ...,
        allowed_mentions: discord.AllowedMentions = ...,
        reference: discord.Message | discord.MessageReference | discord.PartialMessage = ...,
        mention_author: bool = ...,
        view: discord.ui.View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
    ) -> discord.Message: ...

    @overload
    async def reply(
        self,
        content: str | None = ...,
        *,
        tts: bool = ...,
        embeds: Sequence[discord.Embed] = ...,
        file: discord.File = ...,
        stickers: Sequence[discord.GuildSticker | discord.StickerItem] = ...,
        delete_after: float = ...,
        nonce: str | int = ...,
        allowed_mentions: discord.AllowedMentions = ...,
        reference: discord.Message | discord.MessageReference | discord.PartialMessage = ...,
        mention_author: bool = ...,
        view: discord.ui.View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
    ) -> discord.Message: ...

    @overload
    async def reply(
        self,
        content: str | None = ...,
        *,
        tts: bool = ...,
        embeds: Sequence[discord.Embed] = ...,
        files: Sequence[discord.File] = ...,
        stickers: Sequence[discord.GuildSticker | discord.StickerItem] = ...,
        delete_after: float = ...,
        nonce: str | int = ...,
        allowed_mentions: discord.AllowedMentions = ...,
        reference: discord.Message | discord.MessageReference | discord.PartialMessage = ...,
        mention_author: bool = ...,
        view: discord.ui.View = ...,
        suppress_embeds: bool = ...,
        ephemeral: bool = ...,
        silent: bool = ...,
    ) -> discord.Message: ...

    # Literal copy of .reply from the library but with `.to_reference(fail_if_not_exists=False)`
    @override
    @discord.utils.copy_doc(commands.Context.reply)
    async def reply(self, content: str | None = None, **kwargs: Any):
        if self.interaction is None:
            return await super().send(content, reference=self.message.to_reference(fail_if_not_exists=False), **kwargs)
        return await super().send(content, **kwargs)


class AluGuildContext(AluContext):
    """AluContext but in guilds meaning some attributes can be type-narrowed."""

    if TYPE_CHECKING:
        author: discord.Member
        guild: discord.Guild
        channel: discord.VoiceChannel | discord.TextChannel | discord.Thread
        me: discord.Member
