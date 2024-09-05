from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Image Tools",
    emote=Emote.KURU,
    description="Image Tools",
)


class ImageToolsCog(AluCog, category=category):
    ...
