from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Moderation",
    emote=Emote.peepoPolice,
    description="Moderation tools",
)


class ModerationCog(AluCog, category=category):
    ...
