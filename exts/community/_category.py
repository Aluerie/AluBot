from discord import Embed

from utils import AluCog, CategoryPage, const


class CommunityCategory(CategoryPage, name='Aluerie\'s Community', emote=const.Emote.KURU):
    ...


category = CommunityCategory()


class CommunityCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
