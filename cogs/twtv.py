from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Embed, Streaming
from discord.ext import commands, tasks

from .utils.var import Sid, Uid, Rid, Img, Cid, Ems

if TYPE_CHECKING:
    from discord import Member
    from .utils.bot import AluBot


MY_TWITCH_NAME = 'Aluerie'
MY_TWITCH_ID = 180499648


class TwitchCog(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.mystream.start()

    async def cog_load(self) -> None:
        await self.bot.ini_twitch()

    def cog_unload(self) -> None:
        self.mystream.cancel()

    @commands.Cog.listener()
    async def on_presence_update(self, before: Member, after: Member):
        if before.bot or before.activities == after.activities or before.id == Uid.alu:
            return

        guild = self.bot.get_guild(Sid.alu)
        if after.guild != guild:
            return

        stream_rl = guild.get_role(Rid.live_stream)

        stream_after = None
        for item in after.activities:
            if isinstance(item, Streaming):
                stream_after = item

        if stream_rl not in after.roles and stream_after is not None:  # friend started the stream
            await after.add_roles(stream_rl)
        elif stream_rl in after.roles and stream_after is None:  # friend ended the stream
            await after.remove_roles(stream_rl)
        else:
            return

    @tasks.loop(minutes=2)
    async def mystream(self):
        tw = await self.bot.twitch.get_twitch_stream(MY_TWITCH_ID)
        query = """ UPDATE botinfo SET irene_is_live=$1 
                    WHERE id=$2 
                    AND irene_is_live IS DISTINCT FROM $1
                    RETURNING True;
                """
        val = await self.bot.pool.fetchval(query, tw.online, Sid.alu)

        if not (val and tw.online):
            return

        guild = self.bot.get_guild(Sid.alu)
        mention_role = guild.get_role(Rid.stream_lover)
        content = f'{mention_role.mention} and chat, our Highness **@{tw.display_name}** just went live !'
        file = await self.bot.url_to_file(tw.preview_url, filename='twtvpreview.png')
        em = Embed(colour=0x9146FF, title=f'{tw.title}', url=tw.url)
        em.description = (
            f'Playing {tw.game}\n/[Watch Stream]({tw.url}){await self.bot.twitch.last_vod_link(MY_TWITCH_ID)}'
        )
        em.set_author(name=f'{tw.display_name} just went live on Twitch!', icon_url=tw.logo_url, url=tw.url)
        em.set_footer(text=f'Twitch.tv | With love, {guild.me.display_name}', icon_url=Img.twitchtv)
        em.set_thumbnail(url=tw.logo_url)
        em.set_image(url=f'attachment://{file.filename}')
        await guild.get_channel(Cid.stream_notifs).send(content=content, embed=em, file=file)

    @mystream.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class TwitchThanks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener(name='on_member_update')
    async def twitch_sub_role_logs(self, before, after):
        if after.guild.id != Sid.alu:
            return

        guild = self.bot.get_guild(Sid.alu)
        subs_role = guild.get_role(Rid.subs)

        em = Embed(color=0x9678b6)
        em.set_thumbnail(url=after.display_avatar.url)
        em.set_footer(text=f'With love, {guild.me.display_name}')
        if subs_role in after.roles and subs_role not in before.roles:
            em.title = "User got Aluerie's tw.tv sub"
            em.description = f'{after.mention} just got {subs_role.mention} role in this server !'
            em.add_field(name="{0}{0}{0}".format(Ems.peepoNiceDay), value="Thanks for the sub !")
        elif subs_role in before.roles and subs_role not in after.roles:
            em.title = "User lost Aluerie's tw.tv sub"
            em.description = f'{after.mention} lost {subs_role.mention} role in this server !'
            em.add_field(name="{0}{0}{0}".format(Ems.FeelsRainMan), value="Sad news !")
        else:
            return
        await guild.get_channel(Cid.stream_notifs).send(embed=em)


async def setup(bot):
    await bot.add_cog(TwitchCog(bot))
    await bot.add_cog(TwitchThanks(bot))
