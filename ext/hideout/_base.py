from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Hideout",
    emote=Emote.KURU,
    description="Hideout trash",
)


class HideoutCog(AluCog, category=category):
    ...
