from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name="Voice chat",
    emote=const.Emote.Ree,
    description="Text-To-Speech commands",
)


class VoiceChatCog(AluCog, category=category):
    ...
