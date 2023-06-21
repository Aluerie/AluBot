from discord import Embed

from utils import AluCog, CategoryPage, const


class HideoutCategory(CategoryPage, name='Hideout', emote=const.Emote.KURU):
    ...


category = HideoutCategory()


class HideoutCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
