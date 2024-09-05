from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Information",
    emote=Emote.KURU,
    description="Information",
)


class InfoCog(AluCog, category=category):
    ...
