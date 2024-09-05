from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Reminders",
    emote=Emote.DankHatTooBig,
    description="Reminders",
)


class RemindersCog(AluCog, category=category):
    ...
