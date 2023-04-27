from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import discord
from typing_extensions import Self

if TYPE_CHECKING:
    pass


class Rgx:
    whitespaces = r"\s"  # whitespaces
    emote = r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"  # emotes
    nqn = r":(?P<name>[a-zA-Z0-9_]{2,32}):"  # standard emotes
    # emoji = get_emoji_regexp() # use from emoji import get_emoji_regexp for this
    bug_check = r":.*:"
    emote_stats = r"<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>"
    emote_stats_ids = r"<a?:[a-zA-Z0-9_]{2,32}:([0-9]{18,22})>"
    invis_symbol = "[^!-~]+"  # IDK might be huge question mark

    url_danny = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    url_simple = r"(https?://\S+)"


class Sid:
    """Autocomplete-friendly stash for server ids"""

    alu = 702561315478044804
    test = 759916212842659850

    guild_ids = [alu, test]


class Uid:
    """Autocomplete-friendly stash for User ids

    Example Usage: ::

        # Remember that user mentions are
        user_mention = f'<@{Uid.user_id}>'
    """

    alu = 312204139751014400
    bot = 713124699663499274
    yen = 948934071432654929
    lala = 812763204010246174
    mango = 213476188037971968
    nqn = 559426966151757824


class Rid:
    """Autocomplete-friendly stash for Role ids

    Example Usage: ::

        # Remember that role mentions are
        role_mention = f'<@&{Rid.role_id}>'
    """

    plebs = 727492782196916275

    voice = 761475276361826315
    live_stream = 760082390059581471
    discord_mods = 855839522620047420

    level_zero = 852663921085251585
    category_roles_ids = [
        856589983707693087,  # moderation
        852199351808032788,  # activity
        852193537067843634,  # subscription
        852199851840372847,  # special
        851786344354938880,  # games
        852192240306618419,  # notification
        852194400922632262,  # pronoun
        plebs,  # plebs
    ]
    level_roles = []  # maybe fill it later
    ignored_for_logs = [voice, live_stream] + category_roles_ids


class Ems:
    """Emote strings."""

    # alu server non-animated emotes
    bedNerdge = '<:_:855495407110586439>'
    DankApprove = '<:_:853015071042961468>'
    DankHatTooBig = '<:_:855056297098215474>'
    DankFix = '<:_:924285577027784774>'
    Ree = '<:_:735905686910664797>'
    PepoG = '<:_:930335533970911262>'
    PepoBeliever = '<:_:730887642404618314>'
    peepoComfy = '<:_:726438781208756288>'
    FeelsDankMan = '<:_:726441255805911120>'
    PogChampPepe = '<:_:785600902140526642>'
    PepoDetective = '<:_:743988423500628102>'
    peepoHappyDank = '<:_:852928248953831514>'
    peepoRose = '<:_:856262331666923580>'
    PepoRules = '<:_:772399483039907860>'
    Smartge = '<:_:869075184445956156>'
    peepoWave = '<:_:856262331217346571>'
    peepoBlushDank = '<:_:853744336214032384>'
    peepoPlsStepOnMe = '<:_:761174324420935722>'
    FeelsDankManLostHisHat = '<:_:852976573929095198>'

    peepoPolice = '<:_:960004884235690024>'
    Jebaited = '<:_:726450170769703015>'
    peepoNiceDay = '<:_:857224123885158400>'
    DankLove = '<:_:773614700700368927>'

    MadgeThreat = '<:_:854318972102770728>'
    peepoWTF = '<:_:730688500680097862>'
    DankZzz = '<:_:732126852251910144>'

    # alu server ani
    FeelsRainMan = '<a:_:902254223851421796>'
    DankL = '<a:_:1014616758470070353>'

    # wink server non-animated

    github_logo = '<:_:1081677464637550662>'

    bubuSip = '<:_:865033396189921290>'
    bubuGun = '<:_:847805078543007755>'
    bubuChrist = '<:_:847805078769631262>'
    bubuAyaya = '<:_:764835239138164756>'
    slash = '<:_:823159274954817566>'
    TwoBButt = '<:_:853729747846168576>'
    Lewd = '<:_:976604430059331684>'
    DankG = '<:_:998012133948276857>'
    peepoBusiness = '<:_:998157352098340934>'
    peepoMovie = '<:_:998163742741246003>'
    # wink server ani
    # nothing for now

    # general emotes
    Offline = '\N{LARGE RED CIRCLE}'
    Online = '\N{LARGE GREEN CIRCLE}'
    # emotes arrays
    comfy_emotes = [
        "<:peepoComfy:726438781208756288>",
        "<:_:726438781208756288>",
        "<:pepoblanket:595156413974577162>",
        "<:_:595156413974577162>",
    ]
    phone_numbers = [
        '\N{DIGIT ZERO}',
        '\N{DIGIT ONE}',
        '\N{DIGIT TWO}',
        '\N{DIGIT THREE}',
        '\N{DIGIT FOUR}',
        '\N{DIGIT FIVE}',
        '\N{DIGIT SIX}',
        '\N{DIGIT SEVEN}',
        '\N{DIGIT EIGHT}',
        '\N{DIGIT NINE}',
    ]


class Img:
    github = 'https://pics.freeicons.io/uploads/icons/png/4381378511600029534-512.png'
    heart = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/263/purple-heart_1f49c.png"
    twitchtv = (
        "https://cdn3.iconfinder.com/data/icons/"
        "social-messaging-ui-color-shapes-2-free/128/social-twitch-circle-512.png"
    )


class Lmt:
    class Embed:
        sum_all = 6000
        footer_text = 2048
        title = 256
        description = 4096
        field_amount = 25
        field_name = 256
        field_value = 1024


class Clr:
    """My chosen colours"""

    prpl = discord.Colour(0x9678B6)
    rspbrry = discord.Colour(0xC42C48)
    red = discord.Colour(0xFF0000)
    neon = discord.Colour(0x4D4DFF)
    error = discord.Colour(0x800000)
    olive = discord.Colour(0x98BF64)
    reddit = discord.Colour(0xFF4500)
    twitch = discord.Colour(0x9146FF)
    bot_colour = discord.Colour(0x9400D3)

MP_shades = [900, 800, 700, 600, 500, 400, 300, 200, 100, 50]
MP_ShadeTypeHint = Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50]

class MaterialPalette(discord.Colour):
    """Material Design Color Palette
    
    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors
    """

    def __init__(self, value: int):
        super().__init__(value)

    @classmethod
    def red(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0xB71C1C, 0xC62828, 0xD32F2F, 0xE53935, 0xF44336, 0xEF5350, 0xE57373, 0xEF9A9A, 0xFFCDD2, 0xFFEBEE]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def pink(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x880E4F, 0xAD1457, 0xC2185B, 0xD81B60, 0xE91E63, 0xEC407A, 0xF06292, 0xF48FB1, 0xF8BBD0, 0xFCE4EC]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def purple(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x4A148C, 0x6A1B9A, 0x7B1FA2, 0x8E24AA, 0x9C27B0, 0xAB47BC, 0xBA68C8, 0xCE93D8, 0xE1BEE7, 0xF3E5F5]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def deep_purple(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x311B92, 0x4527A0, 0x512DA8, 0x5E35B1, 0x673AB7, 0x7E57C2, 0x9575CD, 0xB39DDB, 0xD1C4E9, 0xEDE7F6]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def indigo(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x1A237E, 0x283593, 0x303F9F, 0x3949AB, 0x3F51B5, 0x5C6BC0, 0x7986CB, 0x9FA8DA, 0xC5CAE9, 0xE8EAF6]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def blue(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x0D47A1, 0x1565C0, 0x1976D2, 0x1E88E5, 0x2196F3, 0x42A5F5, 0x64B5F6, 0x90CAF9, 0xBBDEFB, 0xE3F2FD]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def light_blue(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x01579B, 0x0277BD, 0x0288D1, 0x039BE5, 0x03A9F4, 0x29B6F6, 0x4FC3F7, 0x81D4FA, 0xB3E5FC, 0xE1F5FE]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def cyan(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x006064, 0x00838F, 0x0097A7, 0x00ACC1, 0x00BCD4, 0x26C6DA, 0x4DD0E1, 0x80DEEA, 0xB2EBF2, 0xE0F7FA]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def teal(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x004D40, 0x00695C, 0x00796B, 0x00897B, 0x009688, 0x26A69A, 0x4DB6AC, 0x80CBC4, 0xB2DFDB, 0xE0F2F1]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def green(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x1B5E20, 0x2E7D32, 0x388E3C, 0x43A047, 0x4CAF50, 0x66BB6A, 0x81C784, 0xA5D6A7, 0xC8E6C9, 0xE8F5E9]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def light_green(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x33691E, 0x558B2F, 0x689F38, 0x7CB342, 0x8BC34A, 0x9CCC65, 0xAED581, 0xC5E1A5, 0xDCEDC8, 0xF1F8E9]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def lime(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x827717, 0x9E9D24, 0xAFB42B, 0xC0CA33, 0xCDDC39, 0xD4E157, 0xDCE775, 0xE6EE9C, 0xF0F4C3, 0xF9FBE7]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def yellow(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0xF57F17, 0xF9A825, 0xFBC02D, 0xFDD835, 0xFFEB3B, 0xFFEE58, 0xFFF176, 0xFFF59D, 0xFFF9C4, 0xFFFDE7]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def amber(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0xFF6F00, 0xFF8F00, 0xFFA000, 0xFFB300, 0xFFC107, 0xFFCA28, 0xFFD54F, 0xFFE082, 0xFFECB3, 0xFFF8E1]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def orange(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0xE65100, 0xEF6C00, 0xF57C00, 0xFB8C00, 0xFF9800, 0xFFA726, 0xFFB74D, 0xFFCC80, 0xFFE0B2, 0xFFF3E0]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def deep_orange(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0xBF360C, 0xD84315, 0xE64A19, 0xF4511E, 0xFF5722, 0xFF7043, 0xFF8A65, 0xFFAB91, 0xFFCCBC, 0xFBE9E7]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def brown(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x3E2723, 0x4E342E, 0x5D4037, 0x6D4C41, 0x795548, 0x8D6E63, 0xA1887F, 0xBCAAA4, 0xD7CCC8, 0xEFEBE9]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def gray(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x212121, 0x424242, 0x616161, 0x757575, 0x9E9E9E, 0xBDBDBD, 0xE0E0E0, 0xEEEEEE, 0xF5F5F5, 0xFAFAFA]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def blue_gray(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x263238, 0x37474F, 0x455A64, 0x546E7A, 0x607D8B, 0x78909C, 0x90A4AE, 0xB0BEC5, 0xCFD8DC, 0xECEFF1]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def black(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000]
        return cls(c[MP_shades.index(shade)])

    @classmethod
    def white(cls, *, shade: MP_ShadeTypeHint = 500) -> Self:
        c = [0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF]
        return cls(c[MP_shades.index(shade)])

MAP_shades = [700, 400, 200, 100]
MAP_ShadeTypeHint = Literal[700, 400, 200, 100]

class MaterialAccentPalette(discord.Colour):
    """Material Design Color Palette with Accent Designs
    
    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors
    """

    def __init__(self, value: int):
        super().__init__(value)

    @classmethod
    def red(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0xD50000, 0xFF1744, 0xFF5252, 0xFF8A80]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def pink(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0xC51162, 0xF50057, 0xFF4081, 0xFF80AB]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def purple(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0xAA00FF, 0xD500F9, 0xE040FB, 0xEA80FC]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def deep_purple(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0x6200EA, 0x651FFF, 0x7C4DFF, 0xB388FF]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def indigo(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0x304FFE, 0x3D5AFE, 0x536DFE, 0x8C9EFF]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def blue(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0x2962FF, 0x2979FF, 0x448AFF, 0x82B1FF]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def light_blue(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0x0091EA, 0x00B0FF, 0x40C4FF, 0x80D8FF]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def cyan(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0x00B8D4, 0x00E5FF, 0x18FFFF, 0x84FFFF]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def teal(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0x00BFA5, 0x1DE9B6, 0x64FFDA, 0xA7FFEB]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def green(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0x00C853, 0x00E676, 0x69F0AE, 0xB9F6CA]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def light_green(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0x64DD17, 0x76FF03, 0xB2FF59, 0xCCFF90]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def lime(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0xAEEA00, 0xC6FF00, 0xEEFF41, 0xF4FF81]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def yellow(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0xFFD600, 0xFFEA00, 0xFFFF00, 0xFFFF8D]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def amber(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0xFFAB00, 0xFFC400, 0xFFD740, 0xFFE57F]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def orange(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0xFF6D00, 0xFF9100, 0xFFAB40, 0xFFD180]
        return cls(c[MAP_shades.index(shade)])

    @classmethod
    def deep_orange(cls, *, shade: MAP_ShadeTypeHint = 200) -> Self:
        c = [0xDD2C00, 0xFF3D00, 0xFF6E40, 0xFF9E80]
        return cls(c[MAP_shades.index(shade)])

    # brown, gray, blue_gray, black, white - these colours do not have Accent versions


# aliases
MP = MaterialPalette
MAP = MaterialAccentPalette

if __name__ == '__main__':
    from PIL import Image

    rectangle = Image.new("RGB", (600, 300), str(MP.purple()))
    rectangle.show()
