from __future__ import annotations

import operator
from collections import Counter
from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import app_commands
from discord.ext import commands

from utils import const, errors

from ._base import HideoutCog

if TYPE_CHECKING:
    from collections.abc import Callable

    from bot import AluBot, AluInteraction


class HideoutModeration(HideoutCog):
    """Moderation utilities for Hideout Discord Server."""

    @commands.Cog.listener(name="on_member_join")
    async def jail_bots_kick_people_on_join(self, member: discord.Member) -> None:
        """Jail or kick outsiders.

        * Kicks non-bot accounts from the server if they somehow managed to enter
        * Gives newly entered bot-accounts @Jailed Bots role.
        """
        if member.guild.id == self.bot.hideout.guild.id:
            if member.bot:
                await member.add_roles(self.bot.hideout.jailed_bots_role)
            else:
                await member.kick()

    @app_commands.guilds(const.Guild.hideout)
    @app_commands.command()
    @app_commands.default_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: AluInteraction,
        messages: app_commands.Range[int, 1, 2000] = 100,
        user: discord.User | None = None,
        after: int | None = None,
        before: int | None = None,
        *,
        bot: bool = False,
        webhooks: bool = False,
        require: Literal["any", "all"] = "all",
    ) -> None:
        """\N{POLICE CAR} (#Hideout) Removes messages from the channel.

        Parameters
        ----------
        messages: app_commands.Range[int, 1, 2000] = 100
            Amount of messages to be deleted.
        user: discord.User | None = None
            User to delete messages of. Default: messages from all users will be deleted.
        after: int | None = None
            Search for messages that come after this message ID.
        before: int | None = None
            Search for messages that come before this message ID.
        bot: bool = False
            Remove messages from bots (not webhooks!).
        webhooks: bool = False
            Remove messages from webhooks.
        require: Literal["any", "all"] = "all"
            Whether any or all of the flags should be met before deleting messages. Defaults to "all".

        Sources
        -------
        * RoboDanny's "/purge" command (license MPL v2 from Rapptz/RoboDanny)
            https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/mod.py.
        """
        await interaction.response.defer()

        predicates: list[Callable[[discord.Message], Any]] = []
        if bot:
            if webhooks:
                predicates.append(lambda m: m.author.bot)
            else:
                predicates.append(lambda m: (m.webhook_id is None or m.interaction is not None) and m.author.bot)
        elif webhooks:
            predicates.append(lambda m: m.webhook_id is not None)
        if user:
            predicates.append(lambda m: m.author == user)

        op = all if require == "all" else any

        def predicate(m: discord.Message) -> bool:
            return op(p(m) for p in predicates)

        search_before = discord.Object(id=before) if before else None
        search_after = discord.Object(id=after) if after else None

        assert interaction.channel and not isinstance(
            interaction.channel,
            discord.ForumChannel | discord.CategoryChannel | discord.DMChannel | discord.GroupChannel,
        )
        try:
            deleted = [
                msg
                async for msg in interaction.channel.history(limit=messages, before=search_before, after=search_after)
                if predicate(msg)
            ]
        except discord.Forbidden:
            msg = "I do not have permissions to search for messages."
            raise errors.PermissionsError(msg) from None
        except discord.HTTPException as e:
            msg = f"Error: {e} (try a smaller search?)"
            raise errors.SomethingWentWrong(msg) from None

        for chunk in discord.utils.as_chunks(deleted, 100):
            try:
                await interaction.channel.delete_messages(
                    chunk,
                    reason=f"Action done by {interaction.user} (ID: {interaction.user.id}): Purge",
                )
            except discord.Forbidden:
                msg = "I do not have permissions to delete messages."
                raise errors.PermissionsError(msg) from None
            except discord.HTTPException as e:
                msg = f"Error while deleting: {e}"
                raise errors.SomethingWentWrong(msg) from None

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        deleted_messages = [f"{deleted} message{' was' if deleted == 1 else 's were'} removed."]
        if deleted:
            deleted_messages.append("")
            spammers = sorted(spammers.items(), key=operator.itemgetter(1), reverse=True)
            deleted_messages.extend(f"**{name}**: {count}" for name, count in spammers)

        to_send = "\n".join(deleted_messages)

        if len(to_send) > 2000:
            await interaction.followup.send(f"Successfully removed {deleted} messages.", ephemeral=True)
        else:
            await interaction.followup.send(to_send, ephemeral=True)

    @app_commands.guilds(const.Guild.hideout)
    @app_commands.command()
    @app_commands.default_permissions(manage_messages=True)
    async def spam_chat(self, interaction: AluInteraction) -> None:
        """Make the bot to spam the chat.

        Useful when we want to move some bad messages out of sight,
        but not clear/delete them, like some annoying/flashing images.
        """
        content = "\n".join([const.Emote.DankHatTooBig for _ in range(20)])
        await interaction.response.send_message(const.Emote.DankHatTooBig)
        assert interaction.channel and not isinstance(
            interaction.channel,
            discord.ForumChannel | discord.CategoryChannel | discord.DMChannel | discord.GroupChannel,
        )
        await interaction.channel.send(content)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(HideoutModeration(bot))
