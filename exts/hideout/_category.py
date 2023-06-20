from discord import Embed

from utils import AluCog, ExtCategory, const


class HideoutCategory(ExtCategory, name='Hideout', emote=const.Emote.KURU):
    @property
    def help_embed(self) -> Embed:
        e = Embed(color=const.Colour.prpl())
        e.description = 'wowzers'
        return e


category = HideoutCategory()


class HideoutCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
