from discord import Embed

from utils import AluCog, CategoryPage, const


class InfoCategory(CategoryPage, name='Information', emote=const.Emote.KURU):
    ...


category = InfoCategory()


class InfoCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
