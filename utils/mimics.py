from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, NotRequired, Self, TypedDict, overload, override

import discord
from discord.utils import MISSING

from . import const, errors

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bot import AluBot, AluContext, AluInteraction

    type WebhookSourceChannel = discord.ForumChannel | discord.VoiceChannel | discord.TextChannel | discord.StageChannel


__all__ = (
    "Mimic",
    "Mirror",
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class EmergencySendKwargs(TypedDict):
    content: NotRequired[str]
    files: NotRequired[Sequence[discord.File]]
    embeds: NotRequired[Sequence[discord.Embed]]


class Mimic:
    """Webhook Management for AluBot.

    Centralized WebHook control.

    Examples
    --------
    Many features are way more handy to realize via webhook sending rather than plain bot messages:
        * Mimic Messages to fix Social Links with bad meta-embeds (such as Twitter/Instagram/TikTok)
        * FPC Messages to give the messages avatars of played hero (so it goes into push notification)
        * NQN-like features, i.e. `/apuband` where it sends emote string from the name of the command user

    Note
    ----
    I call it mimic because it's awkward to write `alu_webhook`, when it's not a webhook...
    it's just an extra layer to find or create a webhook for me.

    But "mimic" because I originally used this structure for mimic messages that try to mirror discord members
    via matching avatar/name in `discord.Webhook.send` arguments.
    """

    def __init__(
        self,
        bot: AluBot,
        channel: WebhookSourceChannel,
        thread: discord.Thread | None,
    ) -> None:
        self.bot: AluBot = bot
        self.channel: WebhookSourceChannel = channel
        self.thread: discord.Thread | None = thread

    @classmethod
    def from_channel(cls, bot: AluBot, channel: discord.abc.MessageableChannel) -> Self:
        channel_, thread = cls.get_channel_thread(channel)
        return cls(bot, channel_, thread)

    @classmethod
    def from_interaction(cls, interaction: AluInteraction) -> Self:
        channel, thread = cls.get_channel_thread(interaction.channel)
        return cls(interaction.client, channel, thread)

    @classmethod
    def from_context(cls, ctx: AluContext) -> Self:
        channel, thread = cls.get_channel_thread(ctx.channel)
        return cls(ctx.bot, channel, thread)

    @classmethod
    def from_message(cls, bot: AluBot, message: discord.Message) -> Self:
        channel, thread = cls.get_channel_thread(message.channel)
        return cls(bot, channel, thread)

    @staticmethod
    def get_channel_thread(
        channel: discord.abc.MessageableChannel | discord.interactions.InteractionChannel | None,
    ) -> tuple[WebhookSourceChannel, discord.Thread | None]:
        match channel:
            case discord.ForumChannel() | discord.TextChannel() | discord.VoiceChannel() | discord.StageChannel():
                # one of WebhookSourceChannel types
                return channel, None
            case discord.Thread():
                parent_channel = channel.parent
                if parent_channel is None:
                    msg = f"Somehow we are in a thread {channel!r} with no parent."
                    raise errors.SomethingWentWrong(msg)
                return parent_channel, channel
            case discord.DMChannel() | discord.GroupChannel():
                msg = f"Such functionality is not available in DMS {channel!r}"
                raise errors.ErroneousUsage(msg)
            case discord.PartialMessageable() | discord.CategoryChannel() | None:
                # typechecker moments
                # idk how I'm going to get these types in practice
                msg = f"Got weird type {type(channel)} for {channel!r}."
                raise errors.SomethingWentWrong(msg)

    async def search_database(self) -> discord.Webhook | None:
        log.debug("Step 1. Searching webhooks in the database for channel %r", self.channel)
        query = "SELECT url FROM webhooks WHERE channel_id = $1"
        webhook_url: str | None = await self.bot.pool.fetchval(query, self.channel.id)
        if webhook_url:
            return discord.Webhook.from_url(webhook_url, client=self.bot, bot_token=self.bot.http.token)
        return None

    async def search_owned(self) -> discord.Webhook | None:
        log.debug("Step 2. Searching for owned webhook in the channel %r", self.channel)
        try:
            channel_webhooks = await self.channel.webhooks()
        except discord.Forbidden:
            msg = (
                'I do not have permission to "Manage Webhooks" in this server. '
                "Please, grant me that permission so I can send cool messages using them."
            )
            raise errors.SomethingWentWrong(msg) from None

        owned_webhooks = [wh for wh in channel_webhooks if wh.user == self.bot.user]
        if owned_webhooks:
            for wh in owned_webhooks[1:]:
                log.debug("Deleting unnecessary webhook %r", wh)
                await wh.delete()

            webhook = owned_webhooks[0]
            await self.insert_into_database(
                webhook_id=webhook.id,
                channel_id=self.channel.id,
                guild_id=self.channel.guild.id,
                url=webhook.url,
            )
            return webhook
        return None

    async def report(self, description: str) -> None:
        embed = discord.Embed(color=const.Color.error, description=description)
        if self.thread:
            await self.thread.send(embed=embed)
        else:
            assert not isinstance(self.channel, discord.ForumChannel)  # type checker moment
            await self.channel.send(embed=embed)

    async def create_webhook(self) -> discord.Webhook:
        channel = self.channel
        log.debug("Step 3. Creating a new webhook for channel %r", channel)
        if not channel.permissions_for(channel.guild.me).manage_webhooks:
            msg = (
                "I dont have permission `manage_webhooks`. "
                "Please, ask moderators to grant me it so I can send messages via webhooks."
            )
            raise errors.SomethingWentWrong(msg)

        try:
            webhook = await channel.create_webhook(
                name=self.bot.user.name,  # f"{self.bot.user.name}'s Webhook",
                avatar=await self.bot.user.display_avatar.read(),
                reason=f"To enable extra functionality for {self.bot.user.display_name}",
            )
        except discord.HTTPException:
            msg = (
                "Hey, I'm sorry for writing like this but I need to create a webhook for this channel "
                "for my functionality, but some error occurred... "
                "Do you have 15 webhooks in here? Can you clear it up (15 is max value) :c"
            )
            raise errors.SomethingWentWrong(msg) from None

        await self.insert_into_database(
            webhook_id=webhook.id,
            channel_id=self.channel.id,
            guild_id=self.channel.guild.id,
            url=webhook.url,
        )
        return webhook

    async def insert_into_database(self, *, webhook_id: int, channel_id: int, guild_id: int, url: str) -> None:
        query = """
            INSERT INTO webhooks
            (id, channel_id, guild_id, url)
            VALUES ($1, $2, $3, $4)
        """
        await self.bot.pool.execute(query, webhook_id, channel_id, guild_id, url)

    @overload
    async def send(
        self,
        content: str = MISSING,
        *,
        username: str = MISSING,
        avatar_url: Any = MISSING,
        file: discord.File = MISSING,
        files: Sequence[discord.File] = MISSING,
        embed: discord.Embed = MISSING,
        embeds: Sequence[discord.Embed] = MISSING,
        wait: Literal[False] = ...,
        report: bool = ...,
    ) -> None: ...

    @overload
    async def send(
        self,
        content: str = MISSING,
        *,
        username: str = MISSING,
        avatar_url: Any = MISSING,
        file: discord.File = MISSING,
        files: Sequence[discord.File] = MISSING,
        embed: discord.Embed = MISSING,
        embeds: Sequence[discord.Embed] = MISSING,
        wait: Literal[True],
        report: bool = ...,
    ) -> discord.WebhookMessage: ...

    async def send(
        self,
        content: str = MISSING,
        *,
        username: str = MISSING,
        avatar_url: Any = MISSING,
        file: discord.File = MISSING,
        files: Sequence[discord.File] = MISSING,
        embed: discord.Embed = MISSING,
        embeds: Sequence[discord.Embed] = MISSING,
        wait: bool = False,
        report: bool = False,
    ) -> discord.WebhookMessage | None:
        """_summary_.

        Parameters
        ----------
        content
            _description_, by default MISSING
        username
            _description_, by default MISSING
        avatar_url
            _description_, by default MISSING
        file
            _description_, by default MISSING
        files
            _description_, by default MISSING
        embed
            _description_, by default MISSING
        embeds
            _description_, by default MISSING
        wait
            _description_, by default False
        report
            Whether to report Exceptions occurred inside this function or simply raise the error.
            Useful to set to True in `@aluloop` tasks so it sends a warning to the user.
            Unnecessary otherwise because error handlers will correctly send it to the command user.

        Returns
        -------
        discord.WebhookMessage | None
            _description_

        Raises
        ------
        errors.SomethingWentWrong
            _description_
        """
        coros = [
            self.search_database,  # Step 1. Trying to find a webhook in the database
            self.search_owned,  # Step 2. Trying to find an owned webhook in the channel
            self.create_webhook,  # Step 3. Creating a webhook ourselves
        ]
        for coro in coros:
            try:
                webhook = await coro()
            except Exception as exc:
                if report:
                    await self.report(str(exc))
                    continue
                raise

            if webhook:
                # the following "if wait" is a monstrous type-checker moment
                # if you see this a few months later - check if
                # commenting out `if wait` and then changing `wait=True` to `wait=wait` doesn't make pyright go crazy
                # if no - remove if wait all together.
                try:
                    if wait:
                        # WebhookMessage:
                        message = await webhook.send(
                            content=content,
                            username=username,
                            avatar_url=avatar_url,
                            file=file,
                            files=files,
                            embed=embed,
                            embeds=embeds,
                            thread=discord.Object(id=self.thread.id) if self.thread else discord.utils.MISSING,
                            wait=True,
                        )
                    else:
                        # None:
                        message = await webhook.send(
                            content=content,
                            username=username,
                            avatar_url=avatar_url,
                            file=file,
                            files=files,
                            embed=embed,
                            embeds=embeds,
                            thread=discord.Object(id=self.thread.id) if self.thread else discord.utils.MISSING,
                        )
                except discord.NotFound:
                    log.warning("Webhook %r for channel %r is not found", webhook, self.channel)
                else:
                    return message

        # Everything failed so let's try sending just as a bot
        log.debug("Step 4. Emergency send for channel %r", self.channel)
        send_kwargs: EmergencySendKwargs = {
            "content": content,
            "embeds": [embed] if embed else embeds,
            "files": [file] if file else files,
        }
        if self.thread:
            await self.thread.send(**send_kwargs)
        else:
            assert not isinstance(self.channel, discord.ForumChannel)  # type checker moment
            await self.channel.send(**send_kwargs)

        msg = "All 3 steps for webhook send stages failed."
        raise errors.SomethingWentWrong(msg)

    async def get_or_create_webhook(self) -> discord.Webhook:
        """Get or create webhook in the channel."""
        # Step 1. Trying to find a webhook in the database
        if webhook := await self.search_database():
            return webhook

        # Step 2. Trying to find an owned webhook in the channel
        if webhook := await self.search_owned():
            return webhook

        # Step 3. Creating a webhook ourselves
        return await self.create_webhook()


class Mirror(Mimic):
    @override
    async def send(
        self,
        member: discord.Member | discord.User,
        content: str = MISSING,
        *,
        file: discord.File = MISSING,
        files: Sequence[discord.File] = MISSING,
        embed: discord.Embed = MISSING,
        embeds: Sequence[discord.Embed] = MISSING,
    ) -> discord.WebhookMessage:
        message = await super().send(
            content=content,
            username=member.display_name,
            avatar_url=member.display_avatar.url,
            file=file,
            files=files,
            embed=embed,
            embeds=embeds,
            wait=True,
        )
        self.bot.mimic_message_user_mapping[message.id] = member.id
        return message
