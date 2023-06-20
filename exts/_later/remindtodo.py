from __future__ import annotations

from discord import Embed, app_commands
from discord.ext import commands, tasks

from utils import Colour, Guild
from utils import AluContext


class Remind(commands.Cog, name='Reminders, ToDo and AFK commands'):
    """Organize yourself with some instruments"""

    def __init__(self, bot):
        self.bot = bot
        self.active_reminders = {}
        self.check_afks.start()
        self.active_afk = {}

    def cog_unload(self) -> None:
        self.check_afks.cancel()

    @commands.hybrid_command(name='afk', description='Flag you as afk member')
    @app_commands.describe(afk_text='Your custom afk note')
    async def afk(self, ctx: AluContext, *, afk_text: str = '...'):
        """Flags you as afk with your custom afk note ;"""
        if db.session.query(db.a).filter_by(id=ctx.author.id).first() is None:
            db.add_row(db.a, ctx.author.id, name=afk_text)
        else:
            db.set_value(db.a, ctx.author.id, name=afk_text)
        self.active_afk[ctx.author.id] = afk_text
        e = Embed(color=Colour.prpl())
        e.description = f'{ctx.author.mention}, you are flagged as afk with `afk_text`:\n{afk_text}'
        await ctx.reply(embed=e)
        try:
            await ctx.author.edit(nick=f'[AFK] | {ctx.author.display_name}')
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.guild is None:  # message.guild.id != Guild.community:
            return
        if msg.content.startswith('$afk') or msg.content.startswith('~afk'):
            return

        for key in self.active_afk:
            if key in msg.raw_mentions:
                guild = self.bot.get_guild(Guild.community)
                member = guild.get_member(key)
                e = (
                    Embed(colour=Colour.prpl(), title='Afk note:', description=db.get_value(db.a, key, 'name'))
                    .set_author(name=f'Sorry, but {member.display_name} is $afk !', icon_url=member.display_avatar.url)
                    .set_footer(
                        text='PS. Please, consider deleting your ping-message (or just removing ping) '
                        'if you think it will be irrelevant when they come back (I mean seriously)'
                    )
                )
                await msg.channel.send(embed=e)

        async def send_non_afk_em(author, channel):
            e = Embed(
                colour=Colour.prpl(), title='Afk note:', description=db.get_value(db.a, author.id, 'name')
            ).set_author(name=f'{author.display_name} is no longer afk !', icon_url=author.display_avatar.url)
            db.remove_row(db.a, author.id)
            self.active_afk.pop(author.id)
            await channel.send(embed=e)
            try:
                await author.edit(nick=db.get_value(db.m, author.id, 'name'))
            except:
                pass

        if msg.author.id in self.active_afk:
            await send_non_afk_em(msg.author, msg.channel)

        if msg.interaction is not None and msg.interaction.user.id in self.active_afk and msg.interaction.name != 'afk':
            await send_non_afk_em(msg.interaction.user, msg.channel)

    @tasks.loop(minutes=30)
    async def check_afks(self):
        rows = db.session.query(db.a)
        for row in rows:
            if row.id in self.active_afk:
                continue
            self.active_afk[row.id] = row.name

    @check_afks.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Remind(bot))
