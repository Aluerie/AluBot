from __future__ import annotations

import datetime
import inspect
import itertools
import os
import re
import time
from typing import TYPE_CHECKING, List, NamedTuple, Optional

import aiofiles
import discord
import pkg_resources
import psutil
import pygit2
from discord import app_commands
from discord.ext import commands

from utils import AluCog, AluContext
from utils.const import Colour, Emote, Limit

if TYPE_CHECKING:
    pass


class Url(discord.ui.View):
    # TODO : make a helper class out of it
    def __init__(self, url: str, label: str = 'Open', emoji: Optional[str] = None):
        super().__init__()
        self.add_item(discord.ui.Button(label=label, emoji=emoji, url=url))


async def count_lines(
    path: str,
    filetype: str = ".py",
    skip_venv: bool = True,
):
    lines = 0
    for i in os.scandir(path):
        if i.is_file():
            if i.path.endswith(filetype):
                if skip_venv and re.search(r"(\\|/)?venv(\\|/)", i.path):
                    continue
                lines += len((await (await aiofiles.open(i.path, "r", encoding='utf8')).read()).split("\n"))
        elif i.is_dir():
            lines += await count_lines(i.path, filetype)
    return lines


async def count_others(
    path: str,
    filetype: str = ".py",
    file_contains: str = "def",
    skip_venv: bool = True,
):
    line_count = 0
    for i in os.scandir(path):
        if i.is_file():
            if i.path.endswith(filetype):
                if skip_venv and re.search(r"(\\|/)?venv(\\|/)", i.path):
                    continue
                line_count += len(
                    [
                        line
                        for line in (await (await aiofiles.open(i.path, "r", encoding='utf8')).read()).split("\n")
                        if file_contains in line
                    ]
                )
        elif i.is_dir():
            line_count += await count_others(i.path, filetype, file_contains)
    return line_count


def format_commit(commit):
    short, _, _ = commit.message.partition("\n")
    short = short[0:40] + "..." if len(short) > 40 else short
    short_sha2 = commit.hex[0:6]
    commit_tz = datetime.timezone(datetime.timedelta(minutes=commit.commit_time_offset))
    commit_time = datetime.datetime.fromtimestamp(commit.commit_time).astimezone(commit_tz)
    offset = discord.utils.format_dt(commit_time, style="R")
    # todo: change the link below to proper global variable I guess ;
    return f"[`{short_sha2}`](https://github.com/Aluerie/AluBot/commit/{commit.hex}) {short} ({offset})"


def get_latest_commits(limit: int = 5):
    repo = pygit2.Repository("./.git")
    commits = list(itertools.islice(repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), limit))
    return "\n".join(format_commit(c) for c in commits)


class FeedbackModal(discord.ui.Modal, title='Submit Feedback'):
    summary = discord.ui.TextInput(
        label='Summary', placeholder='A brief explanation of what you want', max_length=Limit.Embed.title
    )
    details = discord.ui.TextInput(
        label='Details',
        placeholder='Leave a comment',
        style=discord.TextStyle.long,
        required=False,
        max_length=4000, # 4000 is max apparently, Limit.Embed.description,
    )

    def __init__(self, cog: OtherCog) -> None:
        super().__init__()
        self.cog: OtherCog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = self.cog.feedback_channel
        if channel is None:
            await interaction.response.send_message('Sorry, something went wrong \N{THINKING FACE}', ephemeral=True)
            return

        e = self.cog.get_feedback_embed(interaction, summary=str(self.summary), details=self.details.value)
        await channel.send(embed=e)
        e2 = discord.Embed(
            colour=Colour.prpl(), title='Successfully submitted feedback', description=self.details.value
        )
        await interaction.response.send_message(embed=e2)


class PingTuple(NamedTuple):
    emoji: str
    name: str
    value: float


class OtherCog(AluCog):
    @property
    def feedback_channel(self) -> Optional[discord.TextChannel]:
        # maybe add different channel
        return self.bot.hideout.global_logs

    @commands.command()
    async def hello(self, ctx: AluContext):
        await ctx.reply(f'Hello {Emote.bubuAyaya}')

    @staticmethod
    def get_feedback_embed(
        ctx_ntr: AluContext | discord.Interaction,
        *,
        summary: Optional[str] = None,
        details: Optional[str] = None,
    ) -> discord.Embed:
        e = discord.Embed(title=summary, description=details, colour=Colour.prpl())

        if ctx_ntr.guild is not None:
            e.add_field(name='Server', value=f'{ctx_ntr.guild.name} | ID: {ctx_ntr.guild.id}', inline=False)

        if ctx_ntr.channel is not None:
            e.add_field(name='Channel', value=f'#{ctx_ntr.channel} | ID: {ctx_ntr.channel.id}', inline=False)

        if isinstance(ctx_ntr, discord.Interaction):
            e.timestamp, user = ctx_ntr.created_at, ctx_ntr.user
        else:
            e.timestamp, user = ctx_ntr.message.created_at, ctx_ntr.author
        e.set_author(name=str(user), icon_url=user.display_avatar.url)
        e.set_footer(text=f'Author ID: {user.id}')
        return e

    @commands.command(name='feedback')
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def ext_feedback(self, ctx: AluContext, *, details: str):
        """Give feedback about the bot directly to the bot developer.
        This is a quick way to request features or bug fixes. \
        The bot will DM you about the status of your request if possible/needed.
        You can also open issues/PR on [GitHub](https://github.com/Aluerie/AluBot).
        """

        channel = self.feedback_channel
        if channel is None:
            return

        e = self.get_feedback_embed(ctx, details=details)
        await channel.send(embed=e)
        e2 = discord.Embed(colour=Colour.prpl(), description='Successfully sent feedback')
        await ctx.send(embed=e2)

    @app_commands.command(name='feedback')
    async def slh_feedback(self, ntr: discord.Interaction):
        """Give feedback about the bot directly to the bot developer."""
        await ntr.response.send_modal(FeedbackModal(self))

    @commands.is_owner()
    @commands.command(aliases=['pm'], hidden=True)
    async def dm(self, ctx: AluContext, user: discord.User, *, content: str):
        """Write direct message to {user}."""
        e = discord.Embed(colour=Colour.prpl(), title='Message from a developer')
        e.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        e.description = content
        footer_text = (
            'This message is sent to you in DMs because you had previously submitted feedback or '
            'I found a bug in a command you used, I do not monitor this DM.\n'
            'Please, use `/feedback` if you *need* to answer my message.'
        )
        e.set_footer(text=footer_text)
        await user.send(embed=e)
        e2 = discord.Embed(colour=Colour.prpl(), description='DM successfully sent.')
        await ctx.send(embed=e2)

    @commands.command(aliases=['join'])
    async def invite(self, ctx: AluContext):
        """Show the invite link, so you can add me to your server.
        You can also press "Add to Server" button in my profile.
        """
        # TODO: maybe make slash command out of it too

        # Idk why but I want to weight all these permissions carefully so
        # let's make a table for what we actually need those permissions.
        # The following permissions are taken from https://discord.com/developers/applications/
        # in /oauth2/general Bot Permissions section
        # and should match what that webpage offers.

        # Since I have a weird set of functions that greatly differs for Public/Community/Hideout usage
        # Let's weight them in comparison to give ourselves a reasoning why this or that should be `True`.
        # Maybe I should create separate bots for each
        # At the same time it's quite possible I will make features that are currently community-only to be public
        # This is why I probably should be greedy with permissions
        # After all we are growing into multipurpose bot that can do everything.
        p = discord.Permissions()
        # +-----------------------------+-------------------------+-------------------------+-------------------------+
        # | Permission                  | Public                  | Community               | Hideout                 |
        # +=============================+=========================+=========================+=========================+
        # | General Permissions                                                                                       |
        # +-----------------------------+-------------------------+-------------------------+-------------------------+
        # | View Audit Log              | Emote logging                                                     | <- | <- |
        p.view_audit_log = True
        # | Manage Webhooks             |                         | Mimic User Webhooks  <- |                      <- |
        p.manage_webhooks = True
        # | Read Messages/View Channels | Many-many Set channel functions such as FPC Notifications         | <- | <- |
        p.read_messages = True
        # +-----------------------------+-------------------------+-------------------------+-------------------------+
        # | Text Permissions                                                                                          |
        # +-----------------------------+-------------------------+-------------------------+-------------------------+
        # | Send Messages               | Practically everywhere (i.e. FPC Notifications)                   | <- | <- |
        p.send_messages = True
        # | Manage Messages             | /echo /purge commands, mimic user                                 | <- | <- |
        p.manage_messages = True
        # | Embed Links                 | Practically everywhere (i.e. FPC Notifications)                   | <- | <- |
        p.embed_links = True
        # | Attach Files                | Practically everywhere (i.e. FPC Notifications)                   | <- | <- |
        p.attach_files = True
        # | Read Message History        | Practically everywhere (for ctx.reply)                            | <- | <- |
        p.read_message_history = True
        # | Use External Emojis         | Practically everywhere to use emojis from const.Emotes            | <- | <- |
        p.external_emojis = True
        # | Add Reactions               | ?!:thinking: reactions on @AluBot mentions                        | <- | <- |
        p.add_reactions = True
        # +-----------------------------+-------------------------+-------------------------+-------------------------+
        # | Voice Permissions                                                                                         |
        # +-----------------------------+-------------------------+-------------------------+-------------------------+
        # | Connect                     | TextToSpeech commands                                             | <- | <- |
        p.connect = True
        # | Speak                       | TextToSpeech commands                                             | <- | <- |
        p.speak = True
        # +-----------------------------+-------------------------+-------------------------+-------------------------+

        url = discord.utils.oauth_url(self.bot.client_id, permissions=p)
        v = discord.ui.View(timeout=1)
        v.add_item(discord.ui.Button(emoji="\N{SWAN}", label="Invite Link", url=url))
        await ctx.reply(view=v)

    @commands.hybrid_command(help="Checks the bot\'s ping to Discord")
    async def ping(self, ctx: AluContext):
        pings: List[PingTuple] = []

        typing_start = time.monotonic()
        await ctx.typing()
        typing_ms = (time.monotonic() - typing_start) * 1000
        pings.append(PingTuple('\N{KEYBOARD}', 'Typing', typing_ms))

        start = time.perf_counter()
        message = await ctx.reply("\N{TABLE TENNIS PADDLE AND BALL} Pong!")
        message_ms = (time.perf_counter() - start) * 1000
        pings.append(PingTuple('\N{LOVE LETTER}', 'Message', message_ms))

        latency_ms = self.bot.latency * 1000
        pings.append(PingTuple('\N{SPIDER WEB}', 'Websocket', latency_ms))

        postgres_start = time.perf_counter()
        await self.bot.pool.fetch("SELECT 1")
        postgres_ms = (time.perf_counter() - postgres_start) * 1000
        pings.append(PingTuple('\N{ELEPHANT}', 'Database', postgres_ms))

        average = sum([k.value for k in pings]) / len(pings)
        pings.append(PingTuple('\N{PERMANENT PAPER SIGN}', 'Average', average))

        longest_word_length = max([len(p.name) for p in pings])

        answer = '\n'.join(
            [f"{p.emoji} `{p.name.ljust(longest_word_length, ' ')} | {round(p.value, 3):.3f}ms`" for p in pings]
        )

        # await asyncio.sleep(0.7)
        e = discord.Embed(colour=discord.Colour.dark_embed())
        e.description = answer

        await message.edit(embed=e)

    @commands.hybrid_command(help="Show info about the bot", aliases=["botinfo", "bi"])
    async def about(self, ctx: AluContext):
        """Information about the bot itself."""
        await ctx.defer()
        information = await self.bot.application_info()

        e = discord.Embed(colour=Colour.bot_colour(), description=information.description)
        e.add_field(name="Latest updates:", value=get_latest_commits(limit=3), inline=False)

        e.set_author(name=f"Made by {information.owner}", icon_url=information.owner.display_avatar.url)
        # statistics
        total_members = 0
        total_unique = len(self.bot.users)

        guilds = 0
        for guild in self.bot.guilds:
            guilds += 1
            if guild.unavailable:
                continue
            total_members += guild.member_count or 1

        avg = [(len([m for m in g.members if not m.bot]) / (g.member_count or 1)) * 100 for g in self.bot.guilds]
        e.add_field(
            name="Servers",
            value=f"{guilds} total\n{round(sum(avg) / len(avg), 1)}% avg bot/human",
        )
        e.add_field(name="Members", value=f"{total_members:,} total\n{total_unique:,} unique")

        memory_usage = psutil.Process().memory_full_info().uss / 1024**2
        cpu_usage = psutil.cpu_percent()

        e.add_field(name="Process", value=f"{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU")
        e.add_field(name='Command Stats', value='*stats coming soon*')
        # todo: implement command run total and total amount of slash/text commands in the bot maybe tasks
        e.add_field(
            name="Code stats",
            value=(
                f"Lines: {await count_lines('./', '.py'):,}\n"
                f"Functions: {await count_others('./', '.py', 'def '):,}\n"
                f"Classes: {await count_others('./', '.py', 'class '):,}"
            ),
        )
        # try:
        #     pass
        # except (FileNotFoundError, UnicodeDecodeError):
        #     pass
        e.add_field(
            name="Last reboot",
            value=f"{discord.utils.format_dt(self.bot.launch_time,style='R')}",
        )

        version = pkg_resources.get_distribution("discord.py").version
        e.set_footer(
            text=f"Made with discord.py v{version} \N{SPARKLING HEART}",
            icon_url="https://i.imgur.com/5BFecvA.png",
        )
        await ctx.reply(embed=e)

    @commands.hybrid_command(aliases=["sourcecode", "code"], usage="[command|command.subcommand]")
    async def source(self, ctx: AluContext, *, command: Optional[str] = None):
        """Links to the bots code, or a specific command's"""
        source_url = ctx.bot.repo
        branch = "master"

        license_url = f"{source_url}/blob/master/LICENSE"
        e = discord.Embed(title='MPL Conditions', url=license_url, colour=0x612783)
        e.set_author(name='Code is licensed under MPL', url=license_url)
        e.description = (
            "\N{BLACK CIRCLE} Disclose source\n"
            "\N{BLACK CIRCLE} License and copyright notice\n"
            "\N{BLACK CIRCLE} Same license (file)\n"
            "------------------------------------"
        )

        if command is None:
            return await ctx.reply(embed=e, view=Url(source_url, label="Repository link", emoji=Emote.github_logo))

        if command == "help":
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
            obj = "help"
        else:
            obj = self.bot.get_command(command.replace(".", " "))
            if obj is None:
                raise commands.BadArgument("Couldn't find source for the command")

            # since we found the command we're looking for, presumably anyway, let's
            # try to access the code itself
            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
        if not module.startswith("discord"):
            # not a built-in command
            if filename is None:
                raise commands.BadArgument("Couldn't find source for the command")
            location = os.path.relpath(filename).replace("\\", "/")
        else:
            location = module.replace(".", "/") + ".py"
            source_url = "https://github.com/Rapptz/discord.py"
            branch = "master"

        final_url = f"{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}"
        e.set_footer(text=f"{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}")

        await ctx.reply(
            embed=e,
            view=Url(final_url, label=f"Source code for command \"{str(obj)}\"", emoji=Emote.github_logo),
        )
