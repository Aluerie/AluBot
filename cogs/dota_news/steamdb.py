from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks
from github import Github

from config import GIT_PERSONAL_TOKEN
from utils import AluCog
from utils.const.hideout import copy_dota_info, copy_dota_steam, copy_dota_tweets
from utils.formats import block_function
from utils.github import human_commit
from utils.imgtools import str_to_file
from utils.links import move_link_to_title, replace_tco_links

if TYPE_CHECKING:
    from utils import AluBot


async def get_gitdiff_embed(test_num: int = 0):
    g = Github(GIT_PERSONAL_TOKEN)
    repo = g.get_repo("SteamDatabase/GameTracking-Dota2")
    commits = repo.get_commits()
    e = discord.Embed(colour=0x26425A)
    e.set_author(
        name="GameTracking-Dota2 GitHub",
        icon_url="https://icon-library.com/images/github-icon-white/github-icon-white-5.jpg",
        url=commits[test_num].html_url,
    )
    try:
        e.title = commits[test_num].get_statuses()[0].description
        e.url = commits[test_num].get_statuses()[0].target_url
    except IndexError:
        pass
    # e.set_thumbnail(url='https://steamdb.info/static/logos/512px.png')

    embeds = [e]
    files = []
    human, robot_string = await human_commit(repo, commits, test_num=test_num)
    if len(human) > 4000:  # currently only one embed; #12000:
        e.description = (
            "Humanized patch notes are too big to put into several embeds "
            "thus I attach them into `human_patch_notes.txt` file"
        )
        files.append(str_to_file(human, filename="human_patch_notes.txt"))
    else:
        split_size = 4095
        human_list = [human[x : x + split_size] for x in range(0, len(human), split_size)]
        e.description = human_list[0] if len(human_list) else ""
        for i in human_list[1:]:
            embeds.append(discord.Embed(colour=0x26425A, description=i))

    embeds[-1].set_footer(
        text="Unparsed changes are in file below if any", icon_url="https://steamdb.info/static/logos/32px.png"
    )
    if len(robot_string):
        files.append(str_to_file(robot_string, filename="git.diff"))
    return e.url, embeds, files


class SteamDB(AluCog):
    def cog_load(self) -> None:
        self.bot.ini_github()

    blocked_words = ["Steam Community", "Steam Store"]

    whitelist_words = [
        "https://steamdb.info",
    ]

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        try:
            if msg.channel.id in (copy_dota_info, copy_dota_steam, copy_dota_tweets):
                news_channel = self.bot.community.dota_news
            else:
                return

            if msg.channel.id == copy_dota_info:
                if "https://steamdb.info" in msg.content:
                    url, embeds, files = await get_gitdiff_embed()
                    msg = await news_channel.send(content=f"<{url}>", embeds=embeds)
                    await msg.publish()
                    if len(files):
                        msg = await news_channel.send(files=files)
                        await msg.publish()
                if "https://steamcommunity.com" in msg.content:
                    msg = await news_channel.send(content=msg.content, embeds=msg.embeds, files=msg.attachments)
                    await msg.publish()

            elif msg.channel.id == copy_dota_steam:
                if block_function(msg.content, self.blocked_words, self.whitelist_words):
                    return
                e = discord.Embed(colour=0x171A21, description=msg.content)
                msg = await news_channel.send(embed=e)
                await msg.publish()

            elif msg.channel.id == copy_dota_tweets:
                await asyncio.sleep(2)
                answer = await msg.channel.fetch_message(int(msg.id))
                embeds = [await replace_tco_links(self.bot.session, item) for item in answer.embeds]
                embeds = [move_link_to_title(embed) for embed in embeds]
                if embeds:
                    msg = await news_channel.send(embeds=embeds)
                    await msg.publish()
        except Exception as error:
            await self.bot.send_traceback(error, where="#dota-dota_news copypaste")


class TestGitFeed(AluCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.testing.start()

    def cog_unload(self) -> None:
        self.testing.cancel()

    @tasks.loop(count=1)
    async def testing(self):
        num = 4
        url, embeds, files = await get_gitdiff_embed(test_num=num)
        for embed in embeds:
            await self.bot.hideout.spam.send(content=url, embed=embed)
        if len(files):
            await self.bot.hideout.spam.send(files=files)

    @testing.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @testing.error
    async def testing_error(self, error):
        await self.bot.send_traceback(error, where="Test Git dota-git")


async def setup(bot: AluBot):
    await bot.add_cog(SteamDB(bot))

    if bot.test:
        await bot.add_cog(TestGitFeed(bot))
