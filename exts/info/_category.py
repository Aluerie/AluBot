from discord import Embed

from utils import ExtCategory, const


class InfoCategory(ExtCategory, name='Information', emote=const.Emote.KURU):
    @property
    def help_embed(self) -> Embed:
        e = Embed(color=const.Colour.prpl())
        e.description = 'wowzers'
        return e
