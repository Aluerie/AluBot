from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING, Annotated, Any, Callable, Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluCog, checks, const
from utils.converters import Snowflake
from utils.formats import Plural

if TYPE_CHECKING:
    from utils import AluGuildContext


class PurgeFlags(commands.FlagConverter):
    user: Optional[discord.User] = commands.flag(description="Remove messages from this user", default=None)
    contains: Optional[str] = commands.flag(
        description='Remove messages that contains this string (case sensitive)', default=None
    )
    prefix: Optional[str] = commands.flag(
        description='Remove messages that start with this string (case sensitive)', default=None
    )
    suffix: Optional[str] = commands.flag(
        description='Remove messages that end with this string (case sensitive)', default=None
    )
    after: Annotated[Optional[int], Snowflake] = commands.flag(
        description='Search for messages that come after this message ID', default=None
    )
    before: Annotated[Optional[int], Snowflake] = commands.flag(
        description='Search for messages that come before this message ID', default=None
    )
    bot: bool = commands.flag(description='Remove messages from bots (not webhooks!)', default=False)
    webhooks: bool = commands.flag(description='Remove messages from webhooks', default=False)
    embeds: bool = commands.flag(description='Remove messages that have embeds', default=False)
    files: bool = commands.flag(description='Remove messages that have attachments', default=False)
    emoji: bool = commands.flag(description='Remove messages that have custom emoji', default=False)
    reactions: bool = commands.flag(description='Remove messages that have reactions', default=False)
    require: Literal['any', 'all'] = commands.flag(
        description='Whether any or all of the flags should be met before deleting messages. Defaults to "all"',
        default='all',
    )


class ModerationTools(AluCog):
    @commands.hybrid_command(aliases=['remove'], usage='[search] [flags...]')
    @commands.guild_only()
    @checks.hybrid_permissions_check(manage_messages=True)
    @app_commands.describe(search='How many messages to search for')
    async def purge(
        self, ctx: AluGuildContext, search: Optional[commands.Range[int, 1, 2000]] = None, *, flags: PurgeFlags
    ):
        """Removes messages that meet a criteria.

        This command uses a syntax similar to Discord's search bar.
        The messages are only deleted if all options are met unless
        the `require:` flag is passed to override the behaviour.

        The following flags are valid.

        `user:` Remove messages from the given user.
        `contains:` Remove messages that contain a substring.
        `prefix:` Remove messages that start with a string.
        `suffix:` Remove messages that end with a string.
        `after:` Search for messages that come after this message ID.
        `before:` Search for messages that come before this message ID.
        `bot: yes` Remove messages from bots (not webhooks!)
        `webhooks: yes` Remove messages from webhooks
        `embeds: yes` Remove messages that have embeds
        `files: yes` Remove messages that have attachments
        `emoji: yes` Remove messages that have custom emoji
        `reactions: yes` Remove messages that have reactions
        `require: any or all` Whether any or all flags should be met before deleting messages.

        In order to use this command, you must have Manage Messages permissions.
        Note that the bot needs Manage Messages as well. These commands cannot
        be used in a private message.

        When the command is done doing its work, you will get a message
        detailing which users got removed and how many messages got removed.
        """

        predicates: list[Callable[[discord.Message], Any]] = []
        if flags.bot:
            if flags.webhooks:
                predicates.append(lambda m: m.author.bot)
            else:
                predicates.append(lambda m: (m.webhook_id is None or m.interaction is not None) and m.author.bot)
        elif flags.webhooks:
            predicates.append(lambda m: m.webhook_id is not None)

        if flags.embeds:
            predicates.append(lambda m: len(m.embeds))

        if flags.files:
            predicates.append(lambda m: len(m.attachments))

        if flags.reactions:
            predicates.append(lambda m: len(m.reactions))

        if flags.emoji:
            custom_emoji = re.compile(r'<:(\w+):(\d+)>')
            predicates.append(lambda m: custom_emoji.search(m.content))

        if flags.user:
            predicates.append(lambda m: m.author == flags.user)

        if flags.contains:
            predicates.append(lambda m: flags.contains in m.content)  # type: ignore

        if flags.prefix:
            predicates.append(lambda m: m.content.startswith(flags.prefix))  # type: ignore

        if flags.suffix:
            predicates.append(lambda m: m.content.endswith(flags.suffix))  # type: ignore

        require_prompt = False
        if not predicates:
            # If nothing is passed then default to `True` to emulate ?purge all behaviour
            require_prompt = True
            predicates.append(lambda m: True)

        op = all if flags.require == 'all' else any

        def predicate(m: discord.Message) -> bool:
            r = op(p(m) for p in predicates)
            return r

        if flags.after:
            if search is None:
                search = 2000

        if search is None:
            search = 100

        if require_prompt:
            confirm = await ctx.prompt(content=f'Are you sure you want to delete {Plural(search):message}?', timeout=30)
            if not confirm:
                return await ctx.send('Aborting.')

        before = discord.Object(id=flags.before) if flags.before else None
        after = discord.Object(id=flags.after) if flags.after else None
        await ctx.defer()

        if before is None and ctx.interaction is not None:
            # If no before: is passed and we're in a slash command,
            # the deferred message will be deleted by purge and the followup will not show up.
            # To work around this, we need to get the deferred message's ID and avoid deleting it.
            before = await ctx.interaction.original_response()

        try:
            deleted = await ctx.channel.purge(limit=search, before=before, after=after, check=predicate)
        except discord.Forbidden as e:
            return await ctx.send('I do not have permissions to delete messages.')
        except discord.HTTPException as e:
            return await ctx.send(f'Error: {e} (try a smaller search?)')

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append('')
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'**{name}**: {count}' for name, count in spammers)

        to_send = '\n'.join(messages)

        if len(to_send) > 2000:
            await ctx.reply(f'Successfully removed {deleted} messages.', delete_after=10)
        else:
            await ctx.reply(to_send, delete_after=10)

    @commands.hybrid_command()
    @commands.guild_only()
    @checks.hybrid_permissions_check(manage_messages=True)
    async def spam_chat(self, ctx: AluGuildContext):
        '''Let the bot to spam the chat in case you want
        to move some bad messages out of sight,
        but not clear/delete them, like some annoying/flashing images
        that aren't particularly offensive, just annoying.
        '''
        content = '\n'.join([const.Emote.DankHatTooBig for _ in range(20)])
        await ctx.reply(content=content)


async def setup(bot):
    await bot.add_cog(ModerationTools(bot))
