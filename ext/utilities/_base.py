from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name="Utilities",
    emote=const.Emote.FeelsDankManLostHisHat,
    description="Reminders",
)


class UtilitiesCog(AluCog, category=category):
    ...
