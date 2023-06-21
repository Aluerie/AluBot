from discord import SelectOption

from utils import AluCog, const

category = SelectOption(
    label='About',
    emoji=const.Emote.KURU,
    description='Index category of this menu',
    value=__name__,
)


class MetaCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
