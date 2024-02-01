from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name="Reminders",
    emote=const.Emote.DankHatTooBig,
    description="Reminders",
)


class RemindersCog(AluCog, category=category):
    ...
