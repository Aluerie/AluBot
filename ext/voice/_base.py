from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Voice chat",
    emote=Emote.Ree,
    description="Text-To-Speech commands",
)


class VoiceChatCog(AluCog, category=category):
    ...
