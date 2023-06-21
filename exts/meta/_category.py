from discord import Embed

from utils import AluCog, CategoryPage, const


class MetaCategory(CategoryPage, name='About', emote=const.Emote.KURU):
    ...


category = MetaCategory()


class MetaCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
