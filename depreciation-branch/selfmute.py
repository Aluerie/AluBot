@commands.hybrid_command(name='selfmute', description='Mute yourself for chosen duration')
@app_commands.describe(duration='Choose duration of the mute')
async def selfmute(self, ctx: Context, *, duration: time.FutureTime):
    """
    Anti-addiction feature.
    If you want to detach from my server for some time -
    use this command, and you will not be able to chat for specified `<time_duration>`.
    Duration should satisfy `5 minutes < duration < 30 days`.
    """
    if not timedelta(minutes=4, seconds=59) <= duration.dt - ctx.message.created_at <= timedelta(days=30, seconds=9):
        raise commands.BadArgument(
            'Sorry! Duration of selfmute should satisfy `5 minutes < duration < 30 days`'
        )
    selfmute_rl = ctx.guild.get_role(Rid.selfmuted)

    if ctx.author._roles.has(Rid.selfmuted):
        return await ctx.send(f'Somehow you are already muted {Ems.DankFix}')

    warn_em = Embed(colour=Clr.prpl, title='Confirmation Prompt')
    warn_em.description = (
        f'Are you sure you want to be muted until this time:\n{time.format_tdR(duration.dt)}?\n'
        '**Do not ask the moderators to undo this!**'
    )
    confirm = await ctx.prompt(embed=warn_em)
    if not confirm:
        return await ctx.send('Aborting...', delete_after=5.0)

    await ctx.author.add_roles(selfmute_rl)

    em2 = Embed(colour=Clr.red).set_author(name=f'{ctx.author.display_name} is selfmuted until')
    em2.description = time.format_tdR(duration.dt)
    await ctx.guild.get_channel(Cid.logs).send(embed=em2)

    old_max_id = int(db.session.query(func.max(db.u.id)).scalar() or 0)
    db.add_row(
        db.u,
        1 + old_max_id,
        userid=ctx.author.id,
        channelid=ctx.channel.id,
        dtime=duration.dt,
        reason='Selfmute'
    )
    em = Embed(colour=ctx.author.colour)
    em.description = f'{ctx.author.mention} is self-muted until this time:\n{time.format_tdR(duration.dt)}'
    await ctx.send(embed=em)
    if duration.dt < self.check_mutes.next_iteration.replace(tzinfo=timezone.utc):
        self.bot.loop.create_task(self.fire_the_unmute(1 + old_max_id, ctx.author.id, duration.dt))


@tasks.loop(minutes=30)
async def check_mutes(self):
    for row in db.session.query(db.u):
        if row.dtime.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc) + timedelta(minutes=30):
            if row.id in self.active_mutes:
                continue
            self.active_mutes[row.id] = row
            self.bot.loop.create_task(self.fire_the_unmute(row.id, row.userid, row.dtime))


async def fire_the_unmute(self, id_, userid, dtime):
    dtime = dtime.replace(tzinfo=timezone.utc)
    await sleep_until(dtime)
    guild = self.bot.get_guild(Sid.alu)
    selfmute_rl = guild.get_role(Rid.selfmuted)
    member = guild.get_member(userid)
    await member.remove_roles(selfmute_rl)
    db.remove_row(db.u, id_)
    self.active_mutes.pop(id_, None)


@commands.Cog.listener()
async def on_guild_channel_create(self, channel):
    selfmute_rl = channel.guild.get_role(Rid.selfmuted)
    muted_rl = channel.guild.get_role(Rid.muted)
    await channel.set_permissions(selfmute_rl, view_channel=False)
    await channel.set_permissions(muted_rl, send_messages=False)