from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple, Union

import discord
from discord.ext import commands

from . import errors

if TYPE_CHECKING:
    from . import AluBot, AluContext

    WebhookSourceChannel = Union[discord.ForumChannel, discord.VoiceChannel, discord.TextChannel, discord.StageChannel]


class MimicUserWebhook:
    """This class aims to manage webhooks that are supposed
    to mimic user message for various NQN inspired features

    for example, fix twitter/instagram links for them.
    """

    def __init__(self, *, bot: AluBot, channel: WebhookSourceChannel, thread: Optional[discord.Thread]):
        self.bot: AluBot = bot
        self.channel: WebhookSourceChannel = channel
        self.thread: Optional[discord.Thread] = thread

    @staticmethod
    def get_channel_thread(
        channel: discord.abc.MessageableChannel,
    ) -> Tuple[WebhookSourceChannel, Optional[discord.Thread]]:
        res_channel = channel
        match res_channel:
            case discord.Thread():
                parent_channel = res_channel.parent
                if parent_channel is None:
                    raise TypeError('Somehow we are in a thread with no parent channel.')
                return parent_channel, res_channel
            case discord.DMChannel() | discord.GroupChannel():
                raise TypeError('Such functionality is not available in DMs')
            case discord.PartialMessageable():
                # typechecker moments
                # This type is returned in library in a very few places (only at `Client.get_partial_messageable()`?!)
                # thus it's unlikely we get into this case
                raise TypeError('Unknown error due to not enough data about the channel (PartialMessageable).')
            case _:
                return res_channel, None

    @classmethod
    def from_context(cls, ctx: AluContext):
        channel, thread = cls.get_channel_thread(ctx.channel)
        return cls(bot=ctx.bot, channel=channel, thread=thread)

    @classmethod
    def from_message(cls, bot: AluBot, message: discord.Message):
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
            name=f'{self.bot.user.display_name}\'s Webhook',
            avatar=await self.bot.user.display_avatar.read(),
            reason=f'To enable extra functionality from {self.bot.user.display_name}',
        )

    async def get_or_create(self) -> discord.Webhook:
        # TODO: we probably need to put these `raise` in other places.
        try:
            return await self.get_webhook() or await self.create_webhook()
        except discord.Forbidden:
            raise commands.BotMissingPermissions(['manage_webhooks'])
        except discord.HTTPException:
            raise errors.SomethingWentWrong(
                'An error occurred while creating the webhook for this channel. '
                'Note you can only have 15 webhooks per channel.'
            )

    async def send_user_message(
        self,
        member: discord.Member | discord.User,
        *,
        message: Optional[discord.Message] = None,
        content: str = '',
        embed: discord.Embed = discord.utils.MISSING,
    ):
        wh = await self.get_or_create()
        if message:
            files = [await a.to_file() for a in message.attachments]
        else:
            files = discord.utils.MISSING

        msg = await wh.send(
            content=content,
            username=member.display_name,
            avatar_url=member.display_avatar.url,
            embed=embed,
            files=files,
            thread=discord.Object(id=self.thread.id) if self.thread else discord.utils.MISSING,
            wait=True
        )
        self.bot.mimic_message_user_mapping[msg.id] = member.id
        return msg
