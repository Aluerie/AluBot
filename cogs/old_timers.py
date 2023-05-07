from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import tasks
from numpy.random import randint, seed

from utils import AluCog
from utils.const import Channel, Colour, Emote, Guild, Role, User, DIGITS

if TYPE_CHECKING:
    from asyncpg import Pool

    from utils import AluBot


seed(None)


async def get_the_thing(txt_list, name, pool: Pool):
    query = f'UPDATE botinfo SET {name} = {name} + 1 WHERE id=$1 RETURNING {name}'
    val = await pool.fetchval(query, Guild.community)
    return txt_list[val % len(txt_list)]


daily_reminders_txt = [
    f'Hey chat, don\'t forget to spam some emotes in {Channel.comfy_spam} or {Channel.emote_spam}',
    f'Hey chat, if you see some high/elite MMR streamer pick PA/DW/Muerta - '
    f'don\'t hesitate to ping {User.alu} about it pretty please !',
    'Hey chat, please use channels according to their description',
    f'Hey chat, please use {Role.bots} strictly in {Channel.bot_spam} '
    f'(and {Role.nsfw_bots} in {Channel.nsfw_bot_spam} with exceptions of \n'
    f'\N{DIGIT ZERO}\N{COMBINING ENCLOSING KEYCAP} feel free to use {User.bot} everywhere\n'
    f'\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP} {User.mango} in {Channel.pubs_talk}\n'
    f'\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP} {User.nqn}\'s in-built "free-nitro" functions everywhere',
    f'Hey chat, remember to check `$help` and {Channel.patch_notes}. We have a lot of cool features and '
    f'bot commands. Even more to come in future !',
    'Hey chat, follow me on twitch if you haven\'t done it yet: '
    '[twitch.tv/aluerie](https://www.twitch.tv/aluerie) {0} {0} {0}\n'.format(Emote.DankLove),
    f'Hey chat, you can get list of {Role.bots} available to use in {Channel.bot_spam} and '
    f'{Role.nsfw_bots} in {Channel.nsfw_bot_spam} by respectively checking pins in those channels.',
]


async def get_a_text(pool: Pool):
    return await get_the_thing(daily_reminders_txt, 'curr_timer', pool)


daily_reminders_txt = [
    'Hey chat, check out rules in {0}. Follow them or {1} {1} {1}'.format(Channel.rules, Emote.bubuGun),
    f'Hey chat, remember to grab some roles in {Channel.role_selection} including a custom colour from 140 available !',
    'Hey chat, if you have any suggestions about server/stream/emotes/anything - '
    f'suggest them in {Channel.suggestions} with `$suggest ***` command and discuss them there !',
    'Hey chat, you can set up your birthday date with `$birthday` command for some sweet congratulations '
    f'from us on that day and in {Channel.bday_notifs}.',
    'Hey chat, {0} exist {1} {1} {1}'.format(Channel.confessions, Emote.PepoBeliever),
    f'Hey chat, fix your posture {Emote.PepoBeliever}',
    'Hey chat, remember to smile \N{SLIGHTLY SMILING FACE}',
    'Hey chat, feel free to invite new cool people to this server {0} {0} {0}'.format(Emote.peepoComfy),
    'Hey chat, follow étiquette.',
    f'Hey chat, if you ever forget what prefix/help-command bot you want to use have - just look at its nickname, '
    f'for example, {User.nqn} - means its help command is `++help` and its prefix is `++`',
    f'Hey chat, if you ever see {User.bot} offline (it should be always at the top of the members list online) - '
    'immediately ping me',
    f'Hey chat, if while watching my stream you see some cool moment - clip it and post to {Channel.clips}',
    'Hey chat, remember to stay hydrated ! {0} {0} {0}'.format(Emote.bubuSip),
    f'Hey chat, if you have any problems then {Role.discord_mods} can solve it! Especially if it is about this server',
]


async def get_important_text(pool: Pool):
    return await get_the_thing(daily_reminders_txt, 'curr_important_timer', pool)


async def get_fact_text(pool: Pool):
    async def get_msg_count(pool: Pool):
        query = 'SELECT SUM(msg_count) FROM users'
        val = await pool.fetchval(query)
        return val

    daily_reminders_txt = [
        'Hey chat, this server was created on 22/04/2020.',
        'Hey chat, Aluerie made these "interesting daily fact about this server" messages but has no ideas.',
        f'Hey chat, {await get_msg_count(pool)} messages from people in total were sent in this server '
        f'(which my bot tracked)',
        f'Hey chat, <@135119357008150529> was the very first person to join this server - holy poggers '
        f'{Emote.PogChampPepe}'
        # idea to put there the most chatting person who has the most exp and stuff
    ]
    return await get_the_thing(daily_reminders_txt, 'curr_fact_timer', pool)


async def get_gif_text(pool: Pool):
    daily_reminders_txt = [
        'https://media.discordapp.net/attachments/702561315478044807/950421428732325958/peepoSitSlide.gif'
    ]
    return await get_the_thing(daily_reminders_txt, 'curr_gif_timer', pool)


async def get_rule_text(pool: Pool):
    daily_reminders_txt = [
        'Hey chat, follow étiqueté.',
        f'Hey chat, remember the rule\n{DIGITS[1]} Respect everybody in the server. Be polite.',
        f'Hey chat, remember the rule\n{DIGITS[2]} Keep the chat in English if possible so everyone understands.',
        f'Hey chat, remember the rule\n{DIGITS[3]} No racism, sexism or homophobia.',
        f'Hey chat, remember the rule\n{DIGITS[4]} No offensive language.',
        f'Hey chat, remember the rule\n{DIGITS[5]} Spam is OK. That means as long as it doesn\'t completely clog chat up '
        'and makes it unreadable then it\'s fine. And well #xxx_spam channels are created to be spammed.',
        'Hey chat, follow étiqueté.',
        f'Hey chat, remember the rule\n{DIGITS[6]} No spoilers of any kind '
        '(this includes games stories and IRL-things like movies/tournaments/etc). ',
        f'Hey chat, remember the rule\n{DIGITS[7]} No shady links.',
        f'Hey chat, remember the rule\n{DIGITS[8]} Be talkative, have fun and enjoy your time! :3',
        f'Hey chat, remember the rule\n{DIGITS[9]} Nothing that violates Discord [Terms Of Service]'
        '(https://discord.com/terms) & follow [their guidelines](https://discord.com/guidelines)',
        'Hey chat, remember the rule\n\N{KEYCAP TEN} Don\'t encourage others to break these rules.',
    ]
    return await get_the_thing(daily_reminders_txt, 'curr_timer', pool)


class OldTimers(AluCog):
    async def cog_load(self) -> None:
        self.daily_reminders.start()
        self.daily_important_reminders.start()
        self.daily_fact_reminders.start()
        self.daily_gif_reminders.start()
        self.daily_rule_reminders.start()

    def cog_unload(self) -> None:
        self.daily_reminders.cancel()
        self.daily_important_reminders.cancel()
        self.daily_fact_reminders.cancel()
        self.daily_gif_reminders.cancel()
        self.daily_rule_reminders.cancel()

    async def check_amount_messages(self, msg_amount=10):
        async for msg in self.community.general.history(limit=msg_amount):
            if msg.author == self.bot.user:
                return True
        return False

    async def timer_work(self, title, Colour, description, rlimit=2, msg_num=10):
        if randint(1, 100 + 1) > rlimit or await self.check_amount_messages(msg_amount=msg_num):
            return
        e = discord.Embed(title=title, color=Colour, description=description)
        return await self.community.general.send(embed=e)

    @tasks.loop(minutes=87)
    async def daily_reminders(self):
        await self.timer_work('Daily Message', Colour.prpl(), await get_a_text(self.bot.pool))

    @tasks.loop(minutes=89)
    async def daily_important_reminders(self):
        await self.timer_work('Daily Important Message', Colour.rspbrry(), await get_important_text(self.bot.pool))

    @tasks.loop(minutes=157)
    async def daily_fact_reminders(self):
        await self.timer_work('Daily Fact Message', Colour.neon(), await get_fact_text(self.bot.pool))

    @tasks.loop(minutes=136)
    async def daily_rule_reminders(self):
        await self.timer_work('Daily Rule Message', 0x66FFBF, await get_rule_text(self.bot.pool))

    @tasks.loop(minutes=97)
    async def daily_gif_reminders(self):
        if randint(1, 100 + 1) > 2 or await self.check_amount_messages():
            return
        await self.community.general.send(await get_gif_text(self.bot.pool))

    @daily_reminders.before_loop
    async def daily_reminders_before(self):
        await self.bot.wait_until_ready()

    @daily_important_reminders.before_loop
    async def daily_important_reminders_before(self):
        await self.bot.wait_until_ready()

    @daily_fact_reminders.before_loop
    async def daily_fact_reminders_before(self):
        await self.bot.wait_until_ready()

    @daily_rule_reminders.before_loop
    async def daily_rule_reminders_before(self):
        await self.bot.wait_until_ready()

    @daily_gif_reminders.before_loop
    async def daily_gif_reminders_before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(OldTimers(bot))
