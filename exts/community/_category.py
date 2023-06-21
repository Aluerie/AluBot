from discord import Embed

from utils import AluCog, CategoryPage, const


class CommunityCategory(CategoryPage, name='Aluerie\'s Community', emote=const.Emote.KURU):
    @property
    def help_embed(self) -> Embed:
        e = Embed(color=const.Colour.prpl())
        e.description = 'wowzers'
        return e


category = CommunityCategory()


class CommunityCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
