from discord import Embed

from utils import AluCog, CategoryPage, const


class MetaCategory(CategoryPage, name='Meta', emote=const.Emote.KURU):
    @property
    def help_embed(self) -> Embed:
        e = Embed(color=const.Colour.prpl())
        e.description = 'Meta'
        return e


category = MetaCategory()


class MetaCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
