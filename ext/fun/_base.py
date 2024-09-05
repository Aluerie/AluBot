from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Fun",
    emote=Emote.FeelsDankMan,
    description="Commands to have fun with",
)


class FunCog(AluCog, category=category):
    ...
