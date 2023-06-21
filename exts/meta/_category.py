from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Embed

from utils import AluCog, CategoryPage, const

if TYPE_CHECKING:
    from utils import AluBot


class MetaCategory(
    CategoryPage,
    name='About',
    emote=const.Emote.KURU,
):
    def help_embed(self, embed: Embed, bot: AluBot) -> Embed:
        e = super().help_embed(embed, bot)
        e.description = (
            f'{bot.user.name} is an ultimate multi-purpose bot !\n\n' 'Use dropdown menu below to select a category.'
        )
        e.add_field(name=f'{bot.owner.name}\'s server', value='[Link](https://discord.gg/K8FuDeP)')
        e.add_field(name='GitHub', value='[Link](https://github.com/Aluerie/AluBot)')
        e.add_field(name='Bot Owner', value=f'@{bot.owner}')
        return e


category = MetaCategory()


class MetaCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
