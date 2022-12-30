async def guild_check_work(self, guild: Guild):
    query = 'SELECT trusted_ids FROM botinfo WHERE id=$1'
    trusted_ids = await self.bot.pool.fetchval(query, Sid.alu)

    if guild.owner_id not in trusted_ids:
        def find_txt_channel() -> Union[TextChannel, None]:
            if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                return guild.system_channel
            else:
                for ch in guild.text_channels:
                    perms = ch.permissions_for(guild.me)
                    if perms.send_messages:
                        return ch
            return None

        em = Embed(title='Do not invite me to other guilds, please', colour=Clr.prpl)
        em.description = f"Sorry, I don't like being in guilds that aren't made by Aluerie.\n\nI'm leaving."
        em.set_footer(
            text=f'If you really want the bot in your server then dm {self.bot.owner} with good reasoning',
            icon_url=self.bot.owner.avatar.url
        )
        if channel := find_txt_channel():
            await channel.send(embed=em)
        await guild.leave()


@commands.Cog.listener()
async def on_guild_join(self, guild: Guild):
    await self.guild_check_work(guild)


@tasks.loop(count=1)
async def checkguilds(self):
    for guild in self.bot.guilds:
        await self.guild_check_work(guild)


@checkguilds.error
async def checkguilds_error(self, error):
    await self.bot.send_traceback(error, where='CheckGuilds Task')
    # self.checkguilds.restart()


@checkguilds.before_loop
async def before(self):
    await self.bot.wait_until_ready()