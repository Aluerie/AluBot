"""
This cog is just rude reposting from steamdb resources. 

Unfortunately, I'm clueless about how to get the info from steam itself
And following announcement channels in steamdb discord is not a solution 
because I only need ~1/10 of messages they post in here.

If this ever becomes a problem or my bot becomes big t
hen I will have to rewrite this cog.

But for now I just repost messages I'm interested it to only my channel. 
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from github import Github

from config import DOTA_NEWS_WEBHOOK, GIT_PERSONAL_TOKEN, PINK_TEST_WEBHOOK
from utils import AluCog, aluloop, const
from utils.github import human_commit
from utils.imgtools import str_to_file

if TYPE_CHECKING:
    from bot import AluBot


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

    @property
    def news_channel(self) -> discord.TextChannel:
        return self.community.dota_news

    @discord.utils.cached_property
    def news_webhook(self) -> discord.Webhook:
        return discord.Webhook.from_url(
            url=PINK_TEST_WEBHOOK if self.bot.test else DOTA_NEWS_WEBHOOK,
            client=self.bot,
            session=self.bot.session,
            bot_token=self.bot.http.token,
        )

    # this is a bit shady since I just blatantly copy their messages
    # but Idk, I tried fetching Dota 2 news via different kinds of RSS
    # and my attempts were always 1-2 minutes later than steamdb
    # So until I find a better way or just ask them.
    @commands.Cog.listener("on_message")
    async def filter_steamdb_messages(self, message: discord.Message):
        match message.channel.id:
            case const.Channel.dota_info:
                if "https://steamdb.info" in message.content:
                    url, embeds, files = await get_gitdiff_embed()
                    message = await self.news_channel.send(content=f"<{url}>", embeds=embeds)
                    await message.publish()
                    if len(files):
                        message = await self.news_channel.send(files=files)
                        await message.publish()
                if "https://steamcommunity.com" in message.content:
                    msg = await self.news_webhook.send(content=message.content, wait=True)
                    await msg.publish()


class TestGitFeed(AluCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.testing.start()

    def cog_unload(self) -> None:
        self.testing.cancel()

    @aluloop(count=1)
    async def testing(self):
        num = 4
        url, embeds, files = await get_gitdiff_embed(test_num=num)
        for embed in embeds:
            await self.hideout.spam.send(content=url, embed=embed)
        if len(files):
            await self.hideout.spam.send(files=files)


async def setup(bot: AluBot):
    await bot.add_cog(SteamDB(bot))

    if bot.test:
        await bot.add_cog(TestGitFeed(bot))
