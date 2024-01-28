from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name="Personal Settings",
    emote=const.Emote.DankHatTooBig,  # TODO: change emote
    description="Your personal user settings.",
)


class UserSettingsBaseCog(AluCog, category=category):
    ...
