from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Fun',
    emote=const.Emote.FeelsDankMan,
    description='Fun',
)


class FunCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
