from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Fun',
    emote=const.Emote.FeelsDankMan,
    description='Fun',
)


class FunCog(AluCog, category=category):
    ...
