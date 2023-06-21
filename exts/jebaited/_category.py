from discord import Embed

from utils import AluCog, CategoryPage, const


class JebaitedCategory(CategoryPage, name='Jebaited', emote=const.Emote.KURU):
    ...


category = JebaitedCategory()


class JebaitedCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
