from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name="Fun",
    emote=const.Emote.FeelsDankMan,
    description="Commands to have fun with",
)


class FunCog(AluCog, category=category):
    ...
