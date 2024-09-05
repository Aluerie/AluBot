from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="About",
    emote=Emote.KURU,
    description="Meta info",
)


class MetaCog(AluCog, category=category):
    ...
