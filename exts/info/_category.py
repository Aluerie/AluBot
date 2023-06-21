from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Information',
    emote=const.Emote.KURU,
    description='Information',
)


class InfoCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
