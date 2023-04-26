from __future__ import annotations
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks

from utils import AluCog
from utils.var import Sid, Uid, Rid, Img, Cid

if TYPE_CHECKING:
    from utils import AluBot


MY_TWITCH_NAME = 'Aluerie'
MY_TWITCH_ID = 180499648


class TwitchCog(AluCog):
    async def cog_load(self) -> None:
        await self.bot.ini_twitch()
        self.my_stream.start()

    def cog_unload(self) -> None:
        self.my_stream.cancel()

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if before.bot or before.activities == after.activities or before.id == Uid.alu:
            return

        guild = self.community.guild
        if after.guild != guild:
            return

        stream_rl = self.community.live_stream_role

        stream_after = None
        for item in after.activities:
            if isinstance(item, discord.Streaming):
                stream_after = item

        if stream_rl not in after.roles and stream_after is not None:  # friend started the stream
            await after.add_roles(stream_rl)
        elif stream_rl in after.roles and stream_after is None:  # friend ended the stream
            await after.remove_roles(stream_rl)
        else:
            return

    @tasks.loop(minutes=2)
    async def my_stream(self):
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
        file = await self.bot.imgtools.url_to_file(tw.preview_url, filename='twtvpreview.png')
        e = discord.Embed(colour=0x9146FF, title=f'{tw.title}', url=tw.url)
        e.description = (
            f'Playing {tw.game}\n/[Watch Stream]({tw.url}){await self.bot.twitch.last_vod_link(MY_TWITCH_ID)}'
        )
        e.set_author(name=f'{tw.display_name} just went live on Twitch!', icon_url=tw.logo_url, url=tw.url)
        e.set_footer(text=f'Twitch.tv | With love, {guild.me.display_name}', icon_url=Img.twitchtv)
        e.set_thumbnail(url=tw.logo_url)
        e.set_image(url=f'attachment://{file.filename}')
        await guild.get_channel(Cid.stream_notifs).send(content=content, embed=e, file=file)

    @my_stream.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(TwitchCog(bot))
