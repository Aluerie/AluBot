from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from discord.ext import commands

from bot import AluCog

if TYPE_CHECKING:
    from bot import AluBot, Timer

    class CheckAccRenamesQueryRow(TypedDict):
        player_id: int
        twitch_id: int
        display_name: str


class FPCDatabaseManagement(AluCog):
    """FPC Database Management.

    Commands for bot owner(-s) to add/remove player accounts from the FPC database.
    """

    @commands.Cog.listener("on_fpc_twitch_renames_check_timer_complete")
    async def check_twitch_accounts_renames(self, timer: Timer) -> None:
        """Checks if people in FPC database renamed themselves on twitch.tv.

        I think we're using twitch ids everywhere so this timer is more for convenience matter
        when I'm browsing the database, but still.
        """
        for table_name in ("dota_players", "lol_players"):
            query = f"SELECT player_id, twitch_id, display_name FROM {table_name} WHERE twitch_id IS NOT NULL"
            rows: list[CheckAccRenamesQueryRow] = await self.bot.pool.fetch(query)

            for row in rows:
                # todo: wtf fetch only one user ?!
                user = next(iter(await self.bot.twitch.fetch_users(ids=[row["twitch_id"]])), None)

                if user is None:
                    continue
                if user.display_name != row["display_name"]:
                    query = f"UPDATE {table_name} SET display_name=$1 WHERE player_id=$3"
                    await self.bot.pool.execute(query, user.display_name, row["player_id"])
        # TODO: periodic timer - create a new one
        # TODO: maybe standardize the process of periodic timers
        # TODO: remove twitch_check from other folders
        # TODO: check if it's possible to fire a timer before cogs load in


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FPCDatabaseManagement(bot))
