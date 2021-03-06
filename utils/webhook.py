webhookdict = {}


async def user_webhook(ctx, content=None, embed=None):
    found = 0
    webhook = None
    array = await ctx.channel.webhooks()
    for item in array:
        if item.user == ctx.bot.user:
            webhook = item
            found = 1
            break
    if not found:
        webhook = await ctx.channel.create_webhook(name="{}-1".format(ctx.channel.name))
    msg = await webhook.send(
        content=content,
        embed=embed,
        username=ctx.author.display_name,
        avatar_url=ctx.author.display_avatar.url,
        wait=True,
    )
    if ctx.author.id not in webhookdict:
        webhookdict[ctx.author.id] = [msg.id]
    else:
        webhookdict[ctx.author.id].append(msg.id)
    return webhook


def check_msg_react(userid, msgid):
    # print(webhookdict)
    if userid in webhookdict:
        if msgid in webhookdict[userid]:
            return 1
    return 0
