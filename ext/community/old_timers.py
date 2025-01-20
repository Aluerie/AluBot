from __future__ import annotations

import datetime
import random
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple, TypedDict, override

import discord
from discord.ext import commands

from bot import aluloop
from utils.const import DIGITS, Channel, Colour, Emote, Role, User

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot, Timer

    class OldTimerTimerData(TypedDict):
        """Schema."""

        advice: int
        important: int
        fact: int
        gif: int
        rule: int
        dynamic: int


class DailyEmbedMessageTuple(NamedTuple):
    title: str
    colour: int
    category: str
    message_bank: list[str]


ADVICE_BANK = [
    f"Hey chat, don't forget to spam some emotes in {Channel.comfy_spam} or {Channel.emote_spam}",
    f"Hey chat, if you see some high/elite MMR streamer pick PA/DW/Muerta - "
    f"don't hesitate to ping {User.aluerie} about it pretty please !",
    "Hey chat, please use channels according to their description",
    f"Hey chat, please use {Role.bots} strictly in {Channel.bot_spam} "
    f"(and {Role.nsfw_bots} in {Channel.nsfw_bot_spam} with exceptions of \n"
    f"\N{DIGIT ZERO}\N{COMBINING ENCLOSING KEYCAP} feel free to use {User.alubot} everywhere\n"
    f"\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP} {User.mango} in {Channel.pubs_talk}\n"
    f'\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP} {User.nqn}\'s in-built "free-nitro" functions everywhere',
    f"Hey chat, remember to check `$help` and {Channel.patch_notes}. We have a lot of cool features and "
    f"bot commands. Even more to come in future !",
    "Hey chat, follow me on twitch if you haven't done it yet: "
    f"[twitch.tv/aluerie](https://www.twitch.tv/aluerie) {Emote.DankLove} {Emote.DankLove} {Emote.DankLove}\n",
    f"Hey chat, you can get list of {Role.bots} available to use in {Channel.bot_spam} and "
    f"{Role.nsfw_bots} in {Channel.nsfw_bot_spam} by respectively checking pins in those channels.",
]

IMPORTANT_BANK = [
    f"Hey chat, check out rules in {Channel.rules}. Follow them or {Emote.bubuGun} {Emote.bubuGun} {Emote.bubuGun}",
    f"Hey chat, remember to grab some roles in {Channel.role_selection} including a custom colour from 140 available !",
    "Hey chat, if you have any suggestions about server/stream/emotes/anything - "
    f"suggest them in {Channel.suggestions} with `$suggest ***` command and discuss them there !",
    "Hey chat, you can set up your birthday date with `$birthday` command for some sweet congratulations "
    f"from us on that day and in {Channel.bday_notifs}.",
    f"Hey chat, {Channel.confessions} exist {Emote.PepoBeliever} {Emote.PepoBeliever} {Emote.PepoBeliever}",
    f"Hey chat, fix your posture {Emote.PepoBeliever}",
    "Hey chat, remember to smile \N{SLIGHTLY SMILING FACE}",
    "Hey chat, feel free to invite new cool people to this server {0} {0} {0}".format(Emote.peepoComfy),
    "Hey chat, follow étiquette.",
    f"Hey chat, if you ever see {User.alubot} offline (it should be always at the top of the members list online) - "
    "immediately ping me",
    f"Hey chat, if while watching my stream you see some cool moment - clip it and post to {Channel.clips}",
    f"Hey chat, remember to stay hydrated ! {Emote.peepoWater} {Emote.peepoWater} {Emote.peepoWater}",
    f"Hey chat, if you have any problems then {Role.discord_mods} can solve it! Especially if it is about this server",
]


FACT_BANK = [
    "Hey chat, this server was created on 22/04/2020.",
    'Hey chat, Aluerie made these "interesting daily fact about this server" messages but has no ideas.',
    "Hey chat, <@135119357008150529> was the very first person to join this server - holy poggers.",
]

GIF_BANK = [
    "https://media.discordapp.net/attachments/702561315478044807/950421428732325958/peepoSitSlide.gif",
]

RULE_BANK = [
    "Hey chat, follow étiqueté.",
    f"Hey chat, remember the rule\n{DIGITS[1]} Respect everybody in the server. Be polite.",
    f"Hey chat, remember the rule\n{DIGITS[2]} Keep the chat in English if possible so everyone understands.",
    f"Hey chat, remember the rule\n{DIGITS[3]} No racism, sexism or homophobia.",
    f"Hey chat, remember the rule\n{DIGITS[4]} No offensive language.",
    f"Hey chat, remember the rule\n{DIGITS[5]} Spam is OK. That means as long as it doesn't completely clog chat up "
    "and makes it unreadable then it's fine. And well #xxx_spam channels are created to be spammed.",
    "Hey chat, follow étiqueté.",
    f"Hey chat, remember the rule\n{DIGITS[6]} No spoilers of any kind "
    "(this includes games stories and IRL-things like movies/tournaments/etc). ",
    f"Hey chat, remember the rule\n{DIGITS[7]} No shady links.",
    f"Hey chat, remember the rule\n{DIGITS[8]} Be talkative, have fun and enjoy your time! :3",
    f"Hey chat, remember the rule\n{DIGITS[9]} Nothing that violates Discord [Terms Of Service]"
    "(https://discord.com/terms) & follow [their guidelines](https://discord.com/guidelines)",
    "Hey chat, remember the rule\n\N{KEYCAP TEN} Don't encourage others to break these rules.",
]


class DailyEmbedMessageEnum(Enum):
    Simple = DailyEmbedMessageTuple("Daily Message", Colour.blueviolet, "advice", ADVICE_BANK)
    Important = DailyEmbedMessageTuple("Daily Important Message", Colour.darkslategray, "important", IMPORTANT_BANK)
    Fact = DailyEmbedMessageTuple("Daily Fact Message", Colour.slateblue, "fact", FACT_BANK)
    Rule = DailyEmbedMessageTuple("Daily Rule Message", 0x66FFBF, "rule", RULE_BANK)


class OldTimers(CommunityCog):
    """Old Timers."""

    @override
    async def cog_load(self) -> None:
        self.initiate_timer.start()

    @override
    async def cog_unload(self) -> None:
        self.initiate_timer.cancel()

    @aluloop(count=1)
    async def initiate_timer(self) -> None:
        """Initiate Timer."""
        # we have to do this quirk bcs if we put this into cog load
        # it will not have TimerManager initiated yet.
        query = "SELECT id FROM timers WHERE event = $1"
        value = await self.bot.pool.fetchval(query, "old_timer")
        if value:
            # the timer already exists
            return

        # the timer does not exist so we create it (again)
        # probably cog wasn't loaded when event fired
        # which is actually not addressed in the TimerManager logic...
        now = datetime.datetime.now(datetime.UTC)
        data: OldTimerTimerData = {"advice": 0, "important": 0, "dynamic": 0, "fact": 0, "gif": 0, "rule": 0}
        await self.bot.create_timer(
            event="old_timer",
            expires_at=now + datetime.timedelta(hours=20),
            data=data,
        )

    async def get_total_messages_number(self) -> str:
        """Count total amount of messages in the community server (that my bot tracked)."""
        # TODO: please rework this into a simple +1 thing at bot_vars or something
        query = "SELECT SUM(msg_count) FROM community_members"
        val = await self.bot.pool.fetchval(query)
        desc = f"Hey chat, {val} messages from people in total were sent in this server (which my bot tracked)."
        return desc

    @commands.Cog.listener("on_old_timer_timer_complete")
    async def old_timers(self, timer: Timer[OldTimerTimerData]) -> None:
        """Post various reminders or flavour text in #general periodically."""
        async for msg in self.community.general.history(limit=10):
            if msg.author == self.bot.user:
                await self.bot.create_timer(
                    event="old_timer",
                    expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2),
                    data=timer.data,
                )
                return

        timer_type = random.choices(
            population=["embed", "gif", "dynamic"],
            weights=[0.91, 0.08, 0.01],
            k=1,
        )[0]

        match timer_type:
            case "embed":
                # STATIC EMBED MESSAGE
                data = (random.choice(list(DailyEmbedMessageEnum))).value
                timer.data[data.category] = index = timer.data[data.category] + 1

                embed = discord.Embed(
                    colour=data.colour,
                    title=data.title,
                    description=data.message_bank[index % len(data.message_bank)],
                )
                await self.community.general.send(embed=embed)

            case "gif":
                category = "gif"
                timer.data[category] = index = timer.data[category] + 1
                await self.community.general.send(GIF_BANK[index % len(GIF_BANK)])
            case "dynamic":
                coro = random.choice(
                    [
                        self.get_total_messages_number,
                    ]
                )
                desc = await coro()
                embed = discord.Embed(colour=discord.Colour.blue(), title="Dynamic Fact", description=desc)
                await self.community.general.send(embed=embed)
            case _:
                pass

        await self.bot.create_timer(
            event="old_timer",
            expires_at=datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(minutes=random.randint(5 * 60 * 24, 15 * 60 * 24)),
            data=timer.data,
        )


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(OldTimers(bot))
