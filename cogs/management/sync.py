from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

import discord
from discord.ext import commands

from utils.checks import is_owner
from utils import Clr

from ._base import ManagementBaseCog

if TYPE_CHECKING:
    from utils import AluContext


class SyncCommandCog(ManagementBaseCog):
    # **The** famous Umbra\'s sync command holy moly. `?tag usc`. Or `?tag umbra sync command`
    @is_owner()
    @commands.command()
    async def sync(
        self, ctx: AluContext, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None
    ) -> None:
        """Sync command. Usage examples:
        * `$sync` -> global sync
        * `$sync ~` -> sync current guild
        * `$sync *` -> copies all global app commands to current guild and syncs
        * `$sync ^` -> clears all commands from the current guild target and syncs (removes guild commands)
        * `$sync id_1 id_2` -> syncs guilds with id 1 and 2
        """

        e = discord.Embed(colour=Clr.prpl)
        if guilds:
            fmt = 0
            cmds = []
            for guild in guilds:
                try:
                    cmds += await ctx.bot.tree.sync(guild=guild)
                except discord.HTTPException:
                    pass
                else:
                    fmt += 1
            e.description = f"Synced the tree to `{fmt}/{len(guilds)}` guilds."
        elif spec:
            if ctx.guild:
                match spec:
                    case "~":
                        synced = await ctx.bot.tree.sync(guild=ctx.guild)
                    case "*":
                        ctx.bot.tree.copy_global_to(guild=ctx.guild)
                        synced = await ctx.bot.tree.sync(guild=ctx.guild)
                    case "^":
                        ctx.bot.tree.clear_commands(guild=ctx.guild)
                        await ctx.bot.tree.sync(guild=ctx.guild)
                        synced = []
                e.description = f"Synced `{len(synced)}` commands to the current guild."
            else:
                # todo: maybe raise different error
                raise commands.BadArgument("You used `$sync` command with a spec outside of guild")
        else:
            synced = await ctx.bot.tree.sync()
            e.description = f"Synced `{len(synced)}` commands globally."
        await ctx.reply(embed=e)


async def setup(bot):
    await bot.add_cog(SyncCommandCog(bot))
