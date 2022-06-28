from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed
from discord.ext import commands, tasks
from utils.var import Cid, Clr
from utils.format import block_function
from utils.distools import send_traceback
from utils.inettools import replace_tco_links, move_link_to_title, get_links_from_str
from utils.github import human_commit
from utils.imgtools import str_to_file

import asyncio
import tweepy
from github import Github
from os import getenv

if TYPE_CHECKING:
    from discord import Message

consumer_key = getenv('TWITTER_CONSUMER_KEY')
consumer_secret = getenv('TWITTER_CONSUMER_SECRET')
access_token = getenv('TWITTER_ACCESS_TOKEN')
access_token_secret = getenv('TWITTER_ACCESS_TOKEN_SECRET')
bearer_token = getenv('TWITTER_BEARER_TOKEN')
client = tweepy.Client(bearer_token, consumer_key, consumer_secret, access_token, access_token_secret)


async def get_gitdiff_embed(test_num=0):
    g = Github(getenv('GIT_PERSONAL_TOKEN'))
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
                if "https://steamdb.info" not in msg.content:
                    return

                url, embeds, files = await get_gitdiff_embed()
                msg = await self.bot.get_channel(Cid.dota_news).send(
                    content=f'<{url}>',
                    embeds=embeds
                )
                await msg.publish()
                if len(files):
                    msg = await self.bot.get_channel(Cid.dota_news).send(files=files)
                    await msg.publish()

            elif msg.channel.id == Cid.copydota_steam:
                if block_function(msg.content, self.blocked_words, self.whitelist_words):
                    return
                embed = Embed(colour=0x171a21)
                embed.description = msg.content
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
            embed = Embed(colour=Clr.error)
            embed.title = 'Error in  #dota-news copypaste'
            await send_traceback(error, self.bot, embed=embed)


class TestGitFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.testing.start()

    @tasks.loop(count=1)
    async def testing(self):
        test_num = 0
        embeds, files = await get_gitdiff_embed(test_num=test_num)
        for embed in embeds:
            await self.bot.get_channel(Cid.spam_me).send(embed=embed)
        if len(files):
            await self.bot.get_channel(Cid.spam_me).send(files=files)

    @testing.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(CopypasteDota(bot))
    if bot.yen:
        await bot.add_cog(TestGitFeed(bot))
