from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Literal, Optional

import discord
from discord.ext import commands

from utils import aluloop, const, errors

from ._base import DevBaseCog

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class UmbraSyncCommandCog(DevBaseCog):
    """A SPECIAL ONE-COMMAND COG FOR ONE AND ONLY, THE FAMOUS UMBRA SYNC COMMAND. HOLY MOLY!
    (A BIT MODIFIED THO, SORRY UMBRA)

    `?tag usc` which abbreviates to `?tag umbra sync command`.
    """

    @commands.command(hidden=True)
    async def sync(
        self,
        ctx: AluContext,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^", "trust"]] = None,
    ) -> None:
        """Sync AppCommandTree.

        Usage examples:
        * `$sync` -> global sync
        * `$sync ~` -> sync current guild (only its guild-bound commands)
        * `$sync *` -> copies all global app commands to current guild and syncs
        * `$sync ^` -> clears all commands from the current guild target and syncs (removes guild-bound commands)
        * `$sync id_1 id_2` -> syncs guilds with id 1 and 2
        * `$sync trust` -> sync trusted guilds
        """

        # sync to a list of guilds
        async def sync_to_guild_list(guilds: list[discord.Object]) -> tuple[str, str]:
            ret = 0
            cmds = []
            for guild in guilds:
                try:
                    cmds += await ctx.bot.tree.sync(guild=guild)
                except discord.HTTPException:
                    pass
                else:
                    ret += 1
            return (f'`{ret}/{len(guilds)}` guilds', "Synced guild-bound commands to a list of guilds.")

        if spec == "trust":
            guild_list = [discord.Object(id=guild_id) for guild_id in const.TRUSTED_GUILDS]
            title, desc = await sync_to_guild_list(guild_list)
        elif guilds:
            title, desc = await sync_to_guild_list(guilds)

        # sync to current guild
        elif spec:
            if not ctx.guild:
                raise errors.BadArgument(f"You used `{ctx.clean_prefix}sync` with a spec outside of a guild")

            match spec:
                case "~":
                    # no pre-sync action needed.
                    desc = "Synced guild-bound (`@app_commands.guilds(...`) commands to the current guild."
                case "*":
                    ctx.bot.tree.copy_global_to(guild=ctx.guild)
                    desc = "Copied all global commands to the current guild as guild-bound and synced."
                case "^":
                    ctx.bot.tree.clear_commands(guild=ctx.guild)
                    desc = "Cleared guild-bound commands from the current guild."
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
            title = f'`{len(synced)}` commands'

        # global sync then
        else:
            synced = await ctx.bot.tree.sync()
            title, desc = f"`{len(synced)}` commands", "Synced globally."

        # send the result
        e = discord.Embed(colour=const.Colour.prpl(), title=title, description=desc)
        await ctx.reply(embed=e)


class DailyAutoSync(DevBaseCog):
    """Run syncing app cmd tree once a day per restart.

    `?tag ass` and all. But I'm stupid and forget to sync the tree manually.
    So let the bot sync on the very first 3am per restart. Not that big of a deal.

    Especially when I'm actively developing and really only spend time with testing bot.
    """

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.sync_dict: dict[str, None | int] = {
            'hideout-bound': self.hideout.id,
            'community-bound': self.community.id,
            'global': None,
        }

    async def cog_load(self):
        self.one_time_sync.start()

    async def cog_unload(self):
        self.one_time_sync.cancel()

    @aluloop(time=datetime.time(hour=3, minute=33, second=33, tzinfo=datetime.timezone.utc))
    async def one_time_sync(self):
        if not self.sync_dict:
            # 3 Days restart auto-sync is not needed.
            return

        guild_name, guild_id = self.sync_dict.popitem()  # brings last key, value pair in dict

        guild = discord.Object(id=guild_id) if guild_id else None
        synced = await self.bot.tree.sync(guild=guild)
        desc = f"Synced `{len(synced)}` {guild_name} commands."

        e = discord.Embed(color=0x234234, description=desc, title='3 Days auto-sync')
        await self.hideout.daily_report.send(embed=e)


async def setup(bot):
    await bot.add_cog(UmbraSyncCommandCog(bot))
    await bot.add_cog(DailyAutoSync(bot))
