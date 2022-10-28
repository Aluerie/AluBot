from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from discord import Embed
from discord.ext import commands, tasks
from github import Github

from config import GIT_PERSONAL_TOKEN
from .utils import database as db
from .utils.distools import send_traceback
from .utils.format import block_function
from .utils.github import human_commit
from .utils.imgtools import str_to_file
from .utils.links import replace_tco_links, move_link_to_title
from .utils.var import Cid, Clr, Sid, Img

if TYPE_CHECKING:
    from discord import Message


async def get_gitdiff_embed(test_num=0):
    g = Github(GIT_PERSONAL_TOKEN)
    repo = g.get_repo("SteamDatabase/GameTracking-Dota2")
    commits = repo.get_commits()
    embed = Embed(colour=0x26425A)
    embed.set_author(
        name='GameTracking-Dota2 GitHub',
        icon_url='https://icon-library.com/images/github-icon-white/github-icon-white-5.jpg',
        url=commits[test_num].html_url
    )
    try:
        embed.title = commits[test_num].get_statuses()[0].description
        embed.url = commits[test_num].get_statuses()[0].target_url
    except IndexError:
        pass
    # embed.set_thumbnail(url='https://steamdb.info/static/logos/512px.png')

    embeds = [embed]
    files = []
    human, robot_string = await human_commit(repo, commits, test_num=test_num)
    if len(human) > 4000:  # currently only one embed; #12000:
        embed.description = \
            'Humanized patch notes are too big to put into several embeds ' \
            'thus I attach them into `human_patch_notes.txt` file'
        files.append(str_to_file(human, filename="human_patch_notes.txt"))
    else:
        split_size = 4095
        human_list = [human[x:x + split_size] for x in range(0, len(human), split_size)]
        embed.description = human_list[0] if len(human_list) else ''
        for i in human_list[1:]:
            embeds.append(Embed(colour=0x26425A, description=i))

    embeds[-1].set_footer(
        text='Unparsed changes are in file below if any',
        icon_url='https://steamdb.info/static/logos/32px.png'
    )
    if len(robot_string):
        files.append(str_to_file(robot_string, filename="git.diff"))
    return embed.url, embeds, files


class CopypasteDota(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.patch_checker.start()

    def cog_unload(self) -> None:
        self.patch_checker.cancel()

    blocked_words = [
        'Steam Community',
        'Steam Store'
    ]

    whitelist_words = [
        'https://steamdb.info',
    ]

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        try:
            if msg.channel.id == Cid.copydota_info:
                if "https://steamdb.info" in msg.content:
                    url, embeds, files = await get_gitdiff_embed()
                    msg = await self.bot.get_channel(Cid.dota_news).send(
                        content=f'<{url}>',
                        embeds=embeds
                    )
                    await msg.publish()
                    if len(files):
                        msg = await self.bot.get_channel(Cid.dota_news).send(files=files)
                        await msg.publish()
                if "https://steamcommunity.com" in msg.content:
                    msg = await self.bot.get_channel(Cid.dota_news).send(
                        content=msg.content,
                        embeds=msg.embeds,
                        files=msg.attachments
                    )
                    await msg.publish()

            elif msg.channel.id == Cid.copydota_steam:
                if block_function(msg.content, self.blocked_words, self.whitelist_words):
                    return
                embed = Embed(
                    colour=0x171a21,
                    description=msg.content
                )
                msg = await self.bot.get_channel(Cid.dota_news).send(embed=embed)
                await msg.publish()

            elif msg.channel.id == Cid.copydota_tweets:
                await asyncio.sleep(2)
                answer = await msg.channel.fetch_message(int(msg.id))
                embeds = [await replace_tco_links(self.bot.ses, item) for item in answer.embeds]
                embeds = [move_link_to_title(embed) for embed in embeds]
                if embeds:
                    msg = await self.bot.get_channel(Cid.dota_news).send(embeds=embeds)
                    await msg.publish()
        except Exception as error:
            embed = Embed(
                colour=Clr.error,
                title='Error in  #dota-news copypaste'
            )
            await send_traceback(error, self.bot, embed=embed)

    @tasks.loop(minutes=10)
    async def patch_checker(self):
        url = "https://www.dota2.com/datafeed/patchnoteslist"
        async with self.bot.ses.get(url) as resp:
            data = await resp.json()

        # db.set_value(db.b, Sid.alu, dota_patch='sadge')
        last_patch = data['patches'][-1]
        patch_number, patch_name = last_patch['patch_number'], last_patch['patch_name']

        if patch_number != db.get_value(db.b, Sid.alu, 'dota_patch'):  # New Patch is here
            db.set_value(db.b, Sid.alu, dota_patch=patch_number)

            em = Embed(
                colour=Clr.prpl,
                url=f'https://www.dota2.com/patches/{patch_number}',
                title='Patch Notes',
                description='Hey chat, I think new patch is out!'
            ).set_footer(
                text='I\'m checking Valve\'s datafeed every 10 minutes'
            ).set_author(
                icon_url=Img.dota2logo,
                name=f'Patch {patch_number} is out'
            )
            msg = await self.bot.get_channel(Cid.dota_news).send(embed=em)
            await msg.publish()

    @patch_checker.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class TestGitFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.testing.start()

    def cog_unload(self) -> None:
        self.testing.cancel()

    @tasks.loop(count=1)
    async def testing(self):
        num = 0
        url, embeds, files = await get_gitdiff_embed(test_num=num)
        for embed in embeds:
            await self.bot.get_channel(Cid.spam_me).send(content=url, embed=embed)
        if len(files):
            await self.bot.get_channel(Cid.spam_me).send(files=files)

    @testing.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(CopypasteDota(bot))
    # if bot.yen:
    #     await bot.add_cog(TestGitFeed(bot))
