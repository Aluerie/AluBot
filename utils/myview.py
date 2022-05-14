from discord import Interaction
from discord.ext import pages

from utils.var import *


class MyPaginator(pages.Paginator):
    async def interaction_check(self, ntr: Interaction) -> bool:
        if ntr.user and ntr.user.id in [self.user.id, Uid.irene]:
            return True
        await ntr.response.send_message(
            f'This pagination menu cannot be controlled by you ! {Ems.peepoWTF}',
            ephemeral=True
        )
        return False
