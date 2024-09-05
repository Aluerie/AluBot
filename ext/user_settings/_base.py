from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Personal Settings",
    emote=Emote.DankHatTooBig,  # TODO: change emote
    description="Your personal user settings.",
)


class UserSettingsBaseCog(AluCog, category=category):
    ...
