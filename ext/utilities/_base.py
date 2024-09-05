from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Utilities",
    emote=Emote.FeelsDankManLostHisHat,
    description="Reminders",
)


class UtilitiesCog(AluCog, category=category):
    ...
