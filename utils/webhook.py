from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from discord import Embed

    from .bases.context import AluGuildContext

webhook_dict = {}


async def user_webhook(ctx: AluGuildContext, content: Optional[str] = '', embed: Optional[Embed] = None):
    found = 0
    webhook = None
    array = await ctx.channel.webhooks()
    for item in array:
        if item.user == ctx.bot.user:
            webhook = item
            found = 1
            break
    if not found:
        webhook = await ctx.channel.create_webhook(name=f"{ctx.channel.name}-1")
    msg = await webhook.send(
        content=content,
        embed=embed,
        username=ctx.author.display_name,
        avatar_url=ctx.author.display_avatar.url,
        wait=True,
    )
    if ctx.author.id not in webhook_dict:
        webhook_dict[ctx.author.id] = [msg.id]
    else:
        webhook_dict[ctx.author.id].append(msg.id)
    return webhook


def check_msg_react(userid, msgid):
    # print(webhookdict)
    if userid in webhook_dict:
        if msgid in webhook_dict[userid]:
            return 1
    return 0
