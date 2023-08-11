class Insider(HideoutCog):
    def cog_load(self) -> None:
        self.insider_checker.start()

    def cog_unload(self) -> None:
        self.insider_checker.cancel()

    @aluloop(minutes=10)
    async def insider_checker(self):
        url = "https://blogs.windows.com/windows-insider/feed/"
        rss = feedparser.parse(url)

        for entry in rss.entries:
            if re.findall(r'23[0-9]{3}', entry.title):  # dev entry check
                p = entry
                break
        else:
            return

        query = """ UPDATE botinfo 
                        SET insider_version=$1
                        WHERE id=$2 
                        AND insider_version IS DISTINCT FROM $1
                        RETURNING True
                    """
        val = await self.bot.pool.fetchval(query, p.title, const.Guild.community)
        if not val:
            return

        e = discord.Embed(title=p.title, url=p.link, colour=0x0179D4)
        e.set_image(
            url='https://blogs.windows.com/wp-content/themes/microsoft-stories-theme/img/theme/windows-placeholder.jpg'
        )
        await self.hideout.repost.send(embed=e)