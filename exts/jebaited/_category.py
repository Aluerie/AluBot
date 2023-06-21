from discord import Embed

from utils import AluCog, CategoryPage, const


class JebaitedCategory(CategoryPage, name='Jebaited', emote=const.Emote.KURU):
    @property
    def help_embed(self) -> Embed:
        e = Embed(color=const.Colour.prpl())
        e.description = 'Jebaited'
        return e


category = JebaitedCategory()


class JebaitedCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
