from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Literal, override

import discord
from discord import app_commands
from discord.ext import commands

from utils import aluloop, checks, const, errors

from ._base import DevBaseCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class SyncAppTreeTools(DevBaseCog):
    """A special one-command cog for famous umbra sync command. A bit modified though.

    `?tag usc` which abbreviates to `?tag umbra sync command`.
    """

    @override
    async def cog_load(self) -> None:
        if not self.bot.test:
            self.auto_sync.start()

    @override
    async def cog_unload(self) -> None:
        self.auto_sync.cancel()

    @aluloop(count=1)
    async def auto_sync(self) -> None:
        """Auto syncing bot's application tree task.

        `?tag ass` and all. But I'm stupid and forget to sync the tree manually.
        Especially when I'm actively developing and really only spend time with testing bot.

        Let's do it once per reboot after 2 hours of wait time. If I ever get rate limited warning:
        then we will think of better measures.
        """
        # initial wait
        await asyncio.sleep(60.0 * 60 * 2)  # 2 hours
        # global
        await self.bot.tree.sync()
        # premium guilds
        for guild_id in const.PREMIUM_GUILDS:
            await asyncio.sleep(30.0)
            await self.bot.tree.sync(guild=discord.Object(id=guild_id))

        log.info("Synced global and premium guild bound commands.")

    async def sync_to_guild_list(self, guilds: list[discord.Object]) -> str:
        """Syncs app tree for the guilds."""
        successful_guild_syncs = 0
        cmds = []
        for guild in guilds:
            try:
                cmds += await self.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                successful_guild_syncs += 1
        return f"Synced {len(cmds)} guild-bound commands to `{successful_guild_syncs}/{len(guilds)}` guilds."

    async def sync_command_worker(
        self, spec: str | None, current_guild: discord.Guild | None, guilds: list[discord.Object]
    ) -> discord.Embed:
        # SYNC LIST OF GUILDS
        if spec == "premium":
            guild_list = [discord.Object(id=guild_id) for guild_id in const.PREMIUM_GUILDS]
            desc = await self.sync_to_guild_list(guild_list)
        elif spec == "my":
            guild_list = [discord.Object(id=guild_id) for guild_id in const.MY_GUILDS]
            desc = await self.sync_to_guild_list(guild_list)
        elif guilds:
            desc = await self.sync_to_guild_list(guilds)

        # SYNC METHODS ABOUT CURRENT GUILD
        elif spec and spec != "global":
            if not current_guild:
                msg = "You used `sync` command with a spec outside of a guild"
                raise errors.BadArgument(msg)

            match spec:
                case "current" | "~":
                    # no pre-sync action needed.
                    desc = "Synced `{0}` guild-bound commands to the current guild."
                case "copy" | "*":
                    self.bot.tree.copy_global_to(guild=current_guild)
                    desc = "Copied `{0}` global commands to the current guild and synced."
                case "clear" | "^":
                    self.bot.tree.clear_commands(guild=current_guild)
                    desc = "Cleared guild-bound commands from the current guild."
                case _:
                    msg = "Unknown specification for `sync` command."
                    raise errors.BadArgument(msg)
            synced = await self.bot.tree.sync(guild=current_guild)
            desc = desc.format(len(synced))

        # GLOBAL SYNC THEN
        else:
            synced = await self.bot.tree.sync()
            desc = f"Synced `{len(synced)}` commands globally."

        # return the embed result
        return discord.Embed(colour=const.Colour.blueviolet, description=desc)

    # Unfortunately, we need to split the commands bcs commands.Greedy can't be transferred to app_commands
    @app_commands.command(name="sync")
    @checks.app.is_hideout()
    @app_commands.choices(
        method=[
            app_commands.Choice(name="Global Sync", value="global"),
            app_commands.Choice(name="Current Guild", value="current"),
            app_commands.Choice(name="Copy Global commands to Current Guild", value="copy"),
            app_commands.Choice(name="Clear Current Guild", value="clear"),
            app_commands.Choice(name="Premium Guilds", value="premium"),
            app_commands.Choice(name="My Guilds", value="my"),
            app_commands.Choice(name="Specific Guilds", value="guilds"),
        ]
    )
    async def slash_sync(self, interaction: discord.Interaction[AluBot], method: str) -> None:
        """(\N{GREY HEART} Hideout-Only) Sync bot's app tree.

        Parameters
        ----------
        method : app_commands.Choice[str]
            Method to sync bot's commands with.
        guild_id : Optional[int]
            If you want to sync a specific guild then provide its ID.

        """
        if method == "guilds":
            # it's not worth to mirror commands.Greedy argument into a slash command
            # so just redirect yourself to a prefix $sync command.
            return await interaction.response.send_message(
                f"Use prefix command `{self.bot.main_prefix}`sync guild1_id guild2_id ... ` Dumbass!"
            )

        embed = await self.sync_command_worker(method, interaction.guild, guilds=[])
        await interaction.response.send_message(embed=embed)

    @commands.command(name="sync", hidden=True)
    async def prefix_sync(
        self,
        ctx: AluContext,
        guilds: commands.Greedy[discord.Object],
        spec: Literal["global", "~", "current", "*", "copy", "^", "clear", "premium", "my"] | None = None,
    ) -> None:
        """Sync bot's app tree.

        Usage examples:
        * `$sync` -> global sync
        * `$sync current/~` -> sync current guild (only its guild-bound commands)
        * `$sync copy/*` -> copies all global app commands to current guild and syncs
        * `$sync clear/^` -> clears all commands from the current guild target and syncs (removes guild-bound commands)
        * `$sync id_1 id_2` -> syncs guilds with id 1 and 2
        * `$sync premium` -> sync premium guilds
        * `$sync my` -> sync my guilds
        """
        embed = await self.sync_command_worker(spec, ctx.guild, guilds=guilds)
        await ctx.reply(embed=embed)


class DailyAutoSync(DevBaseCog):
    """Run syncing app cmd tree once per bot restart."""

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)


async def setup(bot: AluBot) -> None:
    await bot.add_cog(SyncAppTreeTools(bot))
    await bot.add_cog(DailyAutoSync(bot))
