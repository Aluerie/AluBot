"""Mimics.

Mimic is what I call a webhook that mimics a human-user by copying their avatar and nickname.
The features in this extensions are aimed to "fix" human's messages:

* Social media embed fixer - a known problem of social networks (instagram, reddit, twitter) where the vanilla metadata-embed
  is lacking. However, for pretty much every social network there exists a "BetterEmbed" service that provides much better
  meta-embeds.

  Similar projects:
  - https://github.com/seriaati/embed-fixer
  - https://betterdiscord.app/plugin/SocialMediaLinkConverter (Now deleted, wtf)

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import re
from typing import TYPE_CHECKING, Any, ClassVar, Literal, NotRequired, Self, TypedDict, overload, override

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import MISSING

from core import AluBot, AluContext, Cog
from shared import clock
from shared.concepts import loop
from utils import const, errors

if TYPE_CHECKING:
    from collections.abc import Sequence

    from core import AluInteraction

    type WebhookSourceChannel = discord.ForumChannel | discord.VoiceChannel | discord.TextChannel | discord.StageChannel

    class EmergencySendKwargs(TypedDict):
        content: NotRequired[str]
        files: NotRequired[Sequence[discord.File]]
        embeds: NotRequired[Sequence[discord.Embed]]

    #########################################################################################################################
    # DATABASE QUERY ROW TYPE-HINTS
    #########################################################################################################################

    class AllWebhooksQueryRow(TypedDict):
        id: int
        channel_id: int
        guild_id: int
        url: str


__all__ = ("MimicsCog",)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Mimic:
    """Webhook Management for AluBot.

    Centralized WebHook control. Some features depend on sending messages via webhooks rather than plain bot messages.
    This class offers a few helping methods.
    """

    def __init__(
        self,
        bot: AluBot,
        channel: WebhookSourceChannel,
        thread: discord.Thread | None,
    ) -> None:
        self.bot: AluBot = bot
        self.channel: WebhookSourceChannel = channel
        self.thread: discord.Thread | None = thread

    @classmethod
    def from_channel(cls, bot: AluBot, channel: discord.abc.MessageableChannel) -> Self:
        """From channel."""
        channel_, thread = cls.get_channel_thread(channel)
        return cls(bot, channel_, thread)

    @classmethod
    def from_interaction(cls, interaction: AluInteraction) -> Self:
        """From interaction."""
        channel, thread = cls.get_channel_thread(interaction.channel)
        return cls(interaction.client, channel, thread)

    @classmethod
    def from_context(cls, ctx: AluContext) -> Self:
        """From context."""
        channel, thread = cls.get_channel_thread(ctx.channel)
        return cls(ctx.bot, channel, thread)

    @classmethod
    def from_message(cls, bot: AluBot, message: discord.Message) -> Self:
        """From message."""
        channel, thread = cls.get_channel_thread(message.channel)
        return cls(bot, channel, thread)

    @staticmethod
    def get_channel_thread(
        channel: discord.abc.MessageableChannel | discord.interactions.InteractionChannel | None,
    ) -> tuple[WebhookSourceChannel, discord.Thread | None]:
        """Get channel thread."""
        match channel:
            case discord.ForumChannel() | discord.TextChannel() | discord.VoiceChannel() | discord.StageChannel():
                # one of WebhookSourceChannel types
                return channel, None
            case discord.Thread():
                parent_channel = channel.parent
                if parent_channel is None:
                    msg = f"Somehow we are in a thread {channel!r} with no parent."
                    raise errors.SomethingWentWrong(msg)
                return parent_channel, channel
            case discord.DMChannel() | discord.GroupChannel():
                msg = f"Such functionality is not available in DMS {channel!r}"
                raise errors.ErroneousUsage(msg)
            case discord.PartialMessageable() | discord.CategoryChannel() | None:
                # typechecker moments
                # idk how I'm going to get these types in practice
                msg = f"Got weird type {type(channel)} for {channel!r}."
                raise errors.SomethingWentWrong(msg)

    async def search_database(self) -> discord.Webhook | None:
        """Search database."""
        log.debug("Step 1. Searching webhooks in the database for channel %r", self.channel)
        query = "SELECT url FROM webhooks WHERE channel_id = $1"
        webhook_url: str | None = await self.bot.pool.fetchval(query, self.channel.id)
        return (
            discord.Webhook.from_url(webhook_url, client=self.bot, bot_token=self.bot.http.token)
            if webhook_url is not None
            else None
        )

    async def search_owned(self) -> discord.Webhook | None:
        """Search owned."""
        log.debug("Step 2. Searching for owned webhook in the channel %r", self.channel)
        try:
            channel_webhooks = await self.channel.webhooks()
        except discord.Forbidden:
            msg = (
                'I do not have permission to "Manage Webhooks" in this server. '
                "Please, grant me that permission so I can send cool messages using them."
            )
            raise errors.SomethingWentWrong(msg) from None

        owned_webhooks = [wh for wh in channel_webhooks if wh.user == self.bot.user]
        if owned_webhooks:
            for webhook in owned_webhooks:
                await self.insert_into_database(
                    webhook_id=webhook.id,
                    channel_id=self.channel.id,
                    guild_id=self.channel.guild.id,
                    url=webhook.url,
                )
            return owned_webhooks[0]
        return None

    async def report(self, description: str) -> None:
        """Report."""
        embed = discord.Embed(color=const.Color.error, description=description)
        if self.thread:
            await self.thread.send(embed=embed)
        else:
            assert not isinstance(self.channel, discord.ForumChannel)  # type checker moment
            await self.channel.send(embed=embed)

    async def create_webhook(self) -> discord.Webhook:
        channel = self.channel
        log.debug("Step 3. Creating a new webhook for channel %r", channel)
        if not channel.permissions_for(channel.guild.me).manage_webhooks:
            msg = (
                "I dont have permission `manage_webhooks`. "
                "Please, ask moderators to grant me it so I can send messages via webhooks."
            )
            raise errors.SomethingWentWrong(msg)

        try:
            webhook = await channel.create_webhook(
                name=self.bot.user.name,  # f"{self.bot.user.name}'s Webhook",
                avatar=await self.bot.user.display_avatar.read(),
                reason=f"To enable extra functionality for {self.bot.user.display_name}",
            )
        except discord.HTTPException:
            msg = (
                "Hey, I'm sorry for writing like this but I need to create a webhook for this channel "
                "for my functionality, but some error occurred... "
                "Do you have 15 webhooks in here? Can you clear it up (15 is max value) :c"
            )
            raise errors.SomethingWentWrong(msg) from None

        await self.insert_into_database(
            webhook_id=webhook.id,
            channel_id=self.channel.id,
            guild_id=self.channel.guild.id,
            url=webhook.url,
        )
        return webhook

    async def insert_into_database(self, *, webhook_id: int, channel_id: int, guild_id: int, url: str) -> None:
        query = """
            INSERT INTO webhooks
            (id, channel_id, guild_id, url)
            VALUES ($1, $2, $3, $4)
        """
        await self.bot.pool.execute(query, webhook_id, channel_id, guild_id, url)

    @overload
    async def send(
        self,
        content: str = MISSING,
        *,
        username: str = MISSING,
        avatar_url: Any = MISSING,
        file: discord.File = MISSING,
        files: Sequence[discord.File] = MISSING,
        embed: discord.Embed = MISSING,
        embeds: Sequence[discord.Embed] = MISSING,
        wait: Literal[False] = ...,
        report: bool = ...,
    ) -> None: ...

    @overload
    async def send(
        self,
        content: str = MISSING,
        *,
        username: str = MISSING,
        avatar_url: Any = MISSING,
        file: discord.File = MISSING,
        files: Sequence[discord.File] = MISSING,
        embed: discord.Embed = MISSING,
        embeds: Sequence[discord.Embed] = MISSING,
        wait: Literal[True],
        report: bool = ...,
    ) -> discord.WebhookMessage: ...

    async def send(
        self,
        content: str = MISSING,
        *,
        username: str = MISSING,
        avatar_url: Any = MISSING,
        file: discord.File = MISSING,
        files: Sequence[discord.File] = MISSING,
        embed: discord.Embed = MISSING,
        embeds: Sequence[discord.Embed] = MISSING,
        wait: bool = False,
        report: bool = False,
    ) -> discord.WebhookMessage | None:
        """_summary_.

        Parameters
        ----------
        content
            _description_, by default MISSING
        username
            _description_, by default MISSING
        avatar_url
            _description_, by default MISSING
        file
            _description_, by default MISSING
        files
            _description_, by default MISSING
        embed
            _description_, by default MISSING
        embeds
            _description_, by default MISSING
        wait
            _description_, by default False
        report
            Whether to report Exceptions occurred inside this function or simply raise the error.
            Useful to set to True in `@aluloop` tasks so it sends a warning to the user.
            Unnecessary otherwise because error handlers will correctly send it to the command user.

        Returns
        -------
        discord.WebhookMessage | None
            _description_

        Raises
        ------
        errors.SomethingWentWrong
            _description_
        """
        get_webhook_methods = [
            self.search_database,  # Step 1. Trying to find a webhook in the database
            self.search_owned,  # Step 2. Trying to find an owned webhook in the channel
            self.create_webhook,  # Step 3. Creating a webhook ourselves
        ]
        for method in get_webhook_methods:
            try:
                webhook = await method()
            except Exception as exc:
                if report:
                    await self.report(str(exc))
                    continue
                raise
            if webhook is None:
                continue

            try:
                message = await webhook.send(
                    content=content,
                    username=username,
                    avatar_url=avatar_url,
                    file=file,
                    files=files,
                    embed=embed,
                    embeds=embeds,
                    thread=discord.Object(id=self.thread.id) if self.thread else discord.utils.MISSING,
                    wait=wait,
                    allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, replied_user=True, users=True),
                )
            except discord.NotFound:
                log.warning("Webhook %r for channel %r is not found", webhook, self.channel)
            else:
                return message

        # Everything failed so let's try sending just as a bot
        log.debug("Step 4. Emergency send for channel %r", self.channel)
        send_kwargs: EmergencySendKwargs = {}
        if content is not MISSING:
            send_kwargs["content"] = content
        if embed is not MISSING:
            send_kwargs["embeds"] = [embed]
        elif embeds is not MISSING:
            send_kwargs["embeds"] = embeds
        if self.thread:
            await self.thread.send(**send_kwargs)
        else:
            assert not isinstance(self.channel, discord.ForumChannel)
            await self.channel.send(**send_kwargs)

        msg = "All 3 steps for webhook send stages failed."
        raise errors.SomethingWentWrong(msg)

    async def get_or_create_webhook(self) -> discord.Webhook:
        """Get or create webhook in the channel."""
        # Step 1. Trying to find a webhook in the database
        if webhook := await self.search_database():
            return webhook

        # Step 2. Trying to find an owned webhook in the channel
        if webhook := await self.search_owned():
            return webhook

        # Step 3. Creating a webhook ourselves
        return await self.create_webhook()


class Mirror(Mimic):
    @override
    async def send(
        self,
        member: discord.Member | discord.User,
        content: str = MISSING,
        *,
        file: discord.File = MISSING,
        files: Sequence[discord.File] = MISSING,
        embed: discord.Embed = MISSING,
        embeds: Sequence[discord.Embed] = MISSING,
    ) -> discord.WebhookMessage:  # ty: ignore[invalid-method-override]
        message = await super().send(
            content=content,
            username=member.display_name,
            avatar_url=member.display_avatar.url,
            file=file,
            files=files,
            embed=embed,
            embeds=embeds,
            wait=True,
        )
        self.bot.mimic_messages[message.id] = member.id
        return message


class MimicsCog(Cog):
    """Mimics."""

    def __init__(self, bot: AluBot) -> None:
        super().__init__(bot)
        self.context_menu_fix_links = app_commands.ContextMenu(
            name="Fix Social Links",
            callback=self.context_menu_fix_links_callback,
        )
        self.context_menu_delete_mimic = app_commands.ContextMenu(
            name="Delete Mimic Message",
            callback=self.context_menu_delete_mimic_callback,
        )

    @override
    async def cog_load(self) -> None:
        await super().cog_load()
        self.check_valid_webhooks.start()
        self.bot.tree.add_command(self.context_menu_fix_links)
        self.bot.tree.add_command(self.context_menu_delete_mimic)

    @override
    async def cog_unload(self) -> None:
        self.check_valid_webhooks.stop()
        self.bot.tree.remove_command(self.context_menu_delete_mimic.name, type=self.context_menu_delete_mimic.type)
        self.bot.tree.remove_command(self.context_menu_fix_links.name, type=self.context_menu_fix_links.type)
        await super().cog_unload()

    #########################################################################################################################
    # EMBED FIXER
    #########################################################################################################################

    SUPPORTED_SITES_DISPLAY_NAMES = (
        # Also remember to edit doc-string for `slash_fix_links`
        "Twitter",
        "Reddit",
        "Instagram",
        "TikTok",
        "DeviantArt",
        "Tumblr",
        "Pixiv",
        "Bsky",
        "Twitch Clips",
        "Spotify",
    )

    FIX_DICT: ClassVar[dict[str, str]] = {
        # mapping: social network -> better embed site,
        # note the "slash" absence in the end and "https://" are important
        # cSpell: disable
        "x": "fxtwitter.com",
        "twitter": "fxtwitter.com",
        "reddit": "vxreddit.com",
        "instagram": "oginstagram.com",
        "tiktok": "tnktok.com",
        "deviantart": "fixdeviantart.com",
        "tumblr": "tpmblr.com",
        "pixiv": "phixiv.net",
        "bsky": "bskyx.app",
        "twitch": "fxtwitch.seria.moe/clip",
        "clips": "fxtwitch.seria.moe/clip",
        "spotify": "fxspotify.com",
        # cSpell: enable
    }

    EMBED_FIXER_REGEX_PATTERN = re.compile(
        pattern=r"""
            # group(0) - the whole URL
            # group(1) - pre URL stuff
            (?P<pre>
            http[s]?
            ://
            (?: [a-zA-Z]+ \.)?  # `www.` or some subdomains like `open.spotify.`
            )
            # group(2) - the actual site host
            (?P<domain>
            x\.com|
            twitter\.com|
            reddit\.com|
            instagram\.com|
            tiktok\.com|
            deviantart\.com|
            tumblr\.com|
            pixiv\.net|
            bsky\.app|
            twitch\.tv/(?:[a-zA-Z]|[0-9]|[_])+/clip|
            clips\.twitch\.tv|
            spotify\.com
            )
            # group(3) - the rest of url
            # it's taken from `?tag url regex` in discord.py server. In a nutshell:
            # letters | digits | some symbols | some more symbols | url %percent-encoded symbols, i.e. %20 for space
            (?P<after>
            / (?: [a-zA-Z] | [0-9] | [$-_@.&+] | [!*(),] | (?:% [0-9a-fA-F][0-9a-fA-F]) )+
            )
        """,
        flags=re.VERBOSE | re.IGNORECASE,  # X = VERBOSE, I = IGNORECASE
    )

    def find_all_social_links_to_fix(self, text: str) -> str:
        """Find common social links in text.

        Parameters
        ----------
        text: str
            Text to search social links in.

        Returns
        -------
        str
            A list of fixed links joined with line-break.
        """
        # Just a reminder on what groups actually are:
        # text = "https://www.instagram.com/p/DBg0L6foRNW/ bla bla bla https://x.com/IceFrog/status/1718834746300719265"
        # for group in EMBED_FIXER_REGEX_PATTERN.findall(text):
        #     print(group)
        #     return
        # >>> tuple('https://www.', 'instagram.com', '/p/DBg0L6foRNW/'), e.g. `group[1] = 'instagram.com'`, etc
        return "\n".join([
            # TODO: replace with group titles too, also in the doc/comment strings
            group[0].replace("www.", "") + self.FIX_DICT[group[1].lower().split(".")[0]] + group[2]
            for group in self.EMBED_FIXER_REGEX_PATTERN.findall(text)
        ])

    def subn_links_to_fix(self, text: str) -> tuple[str, int]:
        """Fix common social links by replacing them with links that provide better meta-embeds for Discord UI.

        Parameters
        ----------
        text: str
            Text to search social links in.

        Returns
        -------
        tuple[str, int]
            `re.subn` returns tuple `(new_string, number_of_subs_made)` which can be useful.

        Sources
        ------
        * https://stackoverflow.com/a/15175239/19217368
        """
        # text = "https://www.instagram.com/p/DBg0L6foRNW/ bla bla bla https://x.com/IceFrog/status/1718834746300719265"
        # mo.group(0) is 'https://www.instagram.com/p/DBg0L6foRNW/'
        # mo.group(1) or mo.group("pre") is 'https://www.'
        # mo.group(2) or mo.group("domain") is 'instagram.com'
        # mo.group(3) or "mo.group("after") is '/p/DBg0L6foRNW/'
        # So `.findall` doesn't include `group(0)` into its groups, which makes sense, but might be confusing.
        return self.EMBED_FIXER_REGEX_PATTERN.subn(
            repl=lambda mo: (
                mo.group("pre").replace("www.", "")
                + self.FIX_DICT[mo.group("domain").lower().split(".")[0]]
                + mo.group("after")
            ),
            string=text,
        )

    def fix_social_links_helper(self, text: str) -> str:
        """Worker embed fixer.

        * slash command;
        * context menu command.
        """
        res = self.find_all_social_links_to_fix(text)
        if not res:
            joined = ";\n".join(f"* {site}" for site in self.SUPPORTED_SITES_DISPLAY_NAMES)
            msg = f'This message does not have any social links to "fix".\n\nCurrently supported:\n{joined}'
            raise commands.BadArgument(msg)
        return res

    async def context_menu_fix_links_callback(self, interaction: AluInteraction, message: discord.Message) -> None:
        """Get better social links from a message."""
        await interaction.response.send_message(self.fix_social_links_helper(message.content))

    @app_commands.command(name="fix-social-links")
    async def slash_fix_social_links(self, interaction: AluInteraction, link: str) -> None:
        """\N{PICK} Enter Social link(-s) to "fix" with a better embed than original.

        Parameters
        ----------
        link: str
            Supported: Twitter, Reddit, Instagram, TikTok, DeviantArt, Tumblr, Pixiv, Bsky, Twitch Clips, Spotify.
        """
        await interaction.response.send_message(self.fix_social_links_helper(link))

    @commands.Cog.listener("on_message")
    async def community_fix_links(self, message: discord.Message) -> None:
        """(#Community Only!) Immediately fix messages with "wrong" social links with "better" ones.

        Currently only enabled in the community and hideout servers.
        """
        if not message.guild or message.guild.id not in const.MY_GUILDS or message.channel.id == const.Channel.jailed_bots:
            # Don't allow outside of community/hideout servers.
            # Don't allow in #jailed_bots as this is where I test other embed fix bots.
            return
        if message.author.bot:
            return

        fixed_message = self.subn_links_to_fix(message.content)
        if fixed_message[1] == 0:
            # Message doesn't have any links to fix
            return

        mirror = Mirror.from_message(bot=self.bot, message=message)
        await mirror.send(message.author, content=fixed_message[0])
        await message.delete()

    TEST_STRINGS: ClassVar[dict[str, int]] = {
        # Number is an amount of expected embed produced if a user sends this string as a message
        # Remember that embeds with multiple images count as many embeds at once (e.g. 4 images = 4 embeds)
        """
        * https://www.instagram.com/taylorswift/p/DXrxObojod9/?hl=en - Taylor Swift;
        * https://instagram.com/reel/CsfO_chhPEe/ - Kuru Cosplay;
        * https://instagram.com/p/DBg0L6foRNW/ - Pale Waves;
        * https://x.com/IceFrog/status/1718834746300719265 - IceFrog;
        * https://open.spotify.com/track/42VUCXerQ5qTr4Qp6PhKo4 - Sabrina Carpenter;
        * https://www.twitch.tv/irene_adler__/clip/SincereCuteOtterBudBlast-tFLu0wQZE6WgrlvD - E33 clip;
        """: 8,
        """
        * https://clips.twitch.tv/SincereCuteOtterBudBlast-tFLu0wQZE6WgrlvD - E33 clip;
        * https://clips.twitch.tv/AmazingVainEelBloodTrail-lWA1mPXy6arU3stT - SB cLip;
        * https://reddit.com/r/DotA2/s/Fjev0bPyO5 - WR Statue post;
        """: 4,
    }

    @commands.command()
    @commands.is_owner()
    async def test_fix_links_examples(self, ctx: AluContext) -> None:
        """Test Fix Link Examples.

        Contains random links that are supposed to be fixed by this cog if they were to be sent by a human.
        """
        results: list[str] = []
        for test_number, (test_string, correct_embed_count) in enumerate(self.TEST_STRINGS.items()):
            await ctx.send(f"# Original Links\n{test_string}", suppress_embeds=True)
            message = await ctx.send(f"# Fixed Links\n{self.subn_links_to_fix(test_string)[0]}")
            await asyncio.sleep(10.0)

            same_message_but_with_meta_embeds = await message.channel.fetch_message(message.id)
            if correct_embed_count != (embed_count := len(same_message_but_with_meta_embeds.embeds)):
                results.append(f"* Test #{test_number + 1} failed: expected {correct_embed_count}, but we got {embed_count}")

        content = "# ❌ Failed\n" + "\n".join(results) if results else "# ✅ All Tests passed"
        await ctx.send(content)

    #########################################################################################################################
    # MIMIC MANAGEMENT
    #########################################################################################################################

    async def context_menu_delete_mimic_callback(self, interaction: AluInteraction, message: discord.Message) -> None:
        """Worker for Application Context Menu command "Delete Mimic Message".

        Allows users to delete bot's messages that are mimicking them.
        """
        if self.bot.mimic_messages.get(message.id) == interaction.user.id:
            # the message is in cache and belongs to the interaction author (user)
            await message.delete()
            embed = discord.Embed(
                color=const.Color.prpl,
                description="Successfully deleted your Mimic message.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not message.webhook_id:
            msg = "This message was not mimicked by my MimicUser functionality."
            raise errors.UserError(msg)

        msg = (
            "Either this message\n"
            "* was not mimicked by me\n"
            "* expired from cache (7 days)\n"
            "* or cache was reset (because of reboot). \nSorry. You have to ask moderators to delete it."
        )
        raise errors.SomethingWentWrong(msg)

    #########################################################################################################################
    # WEBHOOK MAINTENANCE
    #########################################################################################################################

    @commands.Cog.listener(name="on_guild_channel_delete")
    async def deleted_channels(self, channel: discord.abc.GuildChannel) -> None:
        """Delete webhooks associated with a channel from the database when the channel gets deleted."""
        query = "DELETE FROM webhooks WHERE channel_id = $1"
        await self.bot.pool.execute(query, channel.id)

    @commands.Cog.listener(name="on_guild_remove")
    async def removed_guilds(self, guild: discord.Guild) -> None:
        """Delete webhooks associated with a guild from the database when the bot leaves it."""
        query = "DELETE FROM webhooks WHERE guild_id = $1"
        await self.bot.pool.execute(query, guild.id)

    @loop(time=dt.time(hour=13))
    async def check_valid_webhooks(self) -> None:
        """Monthly task to check valid webhooks in the database.

        This cog keeps the table up-to-date, i.e.
        * removes invalid webhooks;
        * checks valid webhooks from time to time;

        Webhooks are used across many of the bot's features so it's important to keep the table updated.
        """
        if clock.utcnow().day != 1:
            return

        query = "SELECT * FROM webhooks"
        rows: list[AllWebhooksQueryRow] = await self.bot.pool.fetch(query)

        for row in rows:
            webhook = self.bot.webhook_from_url(row["url"])

            try:
                webhook = await webhook.fetch()
            except discord.NotFound:
                # webhook is no longer valid
                query = "DELETE FROM webhooks WHERE id = $1"
                await self.bot.pool.execute(query, row["id"])
            else:
                # check if channel is still correct.
                if not webhook.channel:
                    msg = "Webhook channel is None even though we fetched it..."
                    raise errors.PlaceholderError(msg)

                if webhook.channel.id != row["channel_id"]:
                    query = "UPDATE webhooks SET channel_id = $1 WHERE id=$2"
                    await self.bot.pool.execute(query, webhook.channel.id, row["id"])

            await asyncio.sleep(30)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(MimicsCog(bot))
