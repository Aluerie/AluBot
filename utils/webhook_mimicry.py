from __future__ import annotations

from typing import TYPE_CHECKING, Self

import discord
from discord.ext import commands

from . import errors

if TYPE_CHECKING:
    from bot import AluBot, AluContext

    type WebhookSourceChannel = discord.ForumChannel | discord.VoiceChannel | discord.TextChannel | discord.StageChannel


class MimicUserWebhook:
    """Management of Mimic Webhooks and features related to them.

    Mimic Webhook is a discord webhook that aims to mimic user (their profile picture and nickname)
    and posts messages from their name.

    Examples of usage:
    * "Replace" users' messages with bad twitter/instagram links with fixed versions;
    * NQN bot - imitate Nitro emotes;
    """

    def __init__(self, *, bot: AluBot, channel: WebhookSourceChannel, thread: discord.Thread | None) -> None:
        self.bot: AluBot = bot
        self.channel: WebhookSourceChannel = channel
        self.thread: discord.Thread | None = thread

    @staticmethod
    def get_channel_thread(
        channel: discord.abc.MessageableChannel,
    ) -> tuple[WebhookSourceChannel, discord.Thread | None]:
        res_channel = channel
        match res_channel:
            case discord.Thread():
                parent_channel = res_channel.parent
                if parent_channel is None:
                    msg = "Somehow we are in a thread with no parent channel."
                    raise TypeError(msg)
                return parent_channel, res_channel
            case discord.DMChannel() | discord.GroupChannel():
                msg = "Such functionality is not available in DMs"
                raise TypeError(msg)
            case discord.PartialMessageable():
                # typechecker moments
                # This type is returned in library in a very few places (only at `Client.get_partial_messageable()`?!)
                # thus it's unlikely we get into this case
                msg = "Unknown error due to not enough data about the channel (PartialMessageable)."
                raise TypeError(msg)
            case _:
                return res_channel, None

    @classmethod
    def from_context(cls, ctx: AluContext) -> Self:
        channel, thread = cls.get_channel_thread(ctx.channel)
        return cls(bot=ctx.bot, channel=channel, thread=thread)

    @classmethod
    def from_message(cls, bot: AluBot, message: discord.Message) -> Self:
        channel, thread = cls.get_channel_thread(message.channel)
        return cls(bot=bot, channel=channel, thread=thread)

    async def get_webhook(self) -> discord.Webhook | None:
        channel = self.channel
        webhooks = await channel.webhooks()

        owned_webhooks = [wh for wh in webhooks if wh.user == self.bot.user]

        # TODO: idk we might want better rate limiting here.
        # also 15 webhooks per channel thing
        # maybe restructure this whole thing
        # into database/cache because that should be faster?
        if owned_webhooks:
            return owned_webhooks[0]
        else:
            return None

    async def create_webhook(self) -> discord.Webhook:
        return await self.channel.create_webhook(
            name=f"{self.bot.user.display_name}'s Webhook",
            avatar=await self.bot.user.display_avatar.read(),
            reason=f"To enable extra functionality from {self.bot.user.display_name}",
        )

    async def get_or_create(self) -> discord.Webhook:
        # TODO: we probably need to put these `raise` in other places.
        try:
            return await self.get_webhook() or await self.create_webhook()
        except discord.Forbidden:
            raise commands.BotMissingPermissions(["manage_webhooks"])
        except discord.HTTPException:
            msg = (
                "An error occurred while creating the webhook for this channel. "
                "Note you can only have 15 webhooks per channel."
            )
            raise errors.SomethingWentWrong(msg)

    async def send_user_message(
        self,
        member: discord.Member | discord.User,
        *,
        message: discord.Message | None = None,
        content: str = "",
        embed: discord.Embed = discord.utils.MISSING,
    ) -> discord.WebhookMessage:
        wh = await self.get_or_create()
        files = [await a.to_file() for a in message.attachments] if message else discord.utils.MISSING

        msg = await wh.send(
            content=content,
            username=member.display_name,
            avatar_url=member.display_avatar.url,
            embed=embed,
            files=files,
            thread=discord.Object(id=self.thread.id) if self.thread else discord.utils.MISSING,
            wait=True,
        )
        self.bot.mimic_message_user_mapping[msg.id] = member.id
        return msg
