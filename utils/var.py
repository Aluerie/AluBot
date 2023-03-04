from typing import TYPE_CHECKING, Literal, Optional
from typing_extensions import Self

import discord

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
    invis_symb = "[^!-~]+"  # IDK might be huge question mark

    url_danny = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    url_simple = r"(https?://\S+)"


class Sid:
    """Autocomplete-friendly stash for server ids"""

    alu = 702561315478044804
    test = 759916212842659850

    guild_ids = [alu, test]


class Cid:
    """Autocomplete-friendly stash for channel ids

    Example Usage: ::

        # Remember that channel mentions are
        channel_mention = f'<#{Cid.channel_id}>'
    """

    rules = 724996010169991198
    roles = 725941486063190076
    welcome = 725000501690630257
    stream_notifs = 724420415199379557
    clips = 770721052711845929
    bday_notifs = 748604236190842881
    general = 702561315478044807
    pubs_talk = 731376390103892019
    logs = 731615128050598009
    alubot = 724991054474117241
    confessions = 731703242597072896
    weebs = 731887442768166933
    bot_spam = 724986090632642653
    nsfw_bob_spam = 731607736155897978

    stream_room = 766063288302698496

    patch_notes = 731759693113851975
    suggestions = 724994495581782076

    # wink server
    coop = 966366521607745586

    global_logs = 997149550324240465
    spam_logs = 1075497084075130880
    daily_report = 1066406466778566801

    roses = 759916212842659853
    spam_me = 970823670702411810
    test_spam = 1066379298363166791

    repost = 971504469995049041

    copylol_ff20 = 791099728498130944
    copydota_info = 873430376033452053
    copydota_steam = 881843565251141632
    copydota_tweets = 963954743644934184


class Uid:
    """Autocomplete-friendly stash for User ids

    Example Usage: ::

        # Remember that user mentions are
        user_mention = f'<@{Uid.user_id}>'
    """

    alu = 312204139751014400
    bot = 713124699663499274
    yen = 948934071432654929
    mandara = 812763204010246174
    mango = 213476188037971968
    nqn = 559426966151757824


class Rid:
    """Autocomplete-friendly stash for Role ids

    Example Usage: ::

        # Remember that role mentions are
        role_mention = f'<@&{Rid.role_id}>'
    """

    bot_admins = (743509859894558731, 837052934919028746)
    bots = 724981475099017276
    nsfwbots = 959955573405777981
    plebs = 727492782196916275
    subs = 979723279491285012
    milestone = 745716947098009640
    bday = 748586533627363469
    voice = 761475276361826315
    live_stream = 760082390059581471
    friends_stream_lover = 775519667351584778
    stream_lover = 760082003495223298
    rolling_stone = 819096910848851988
    discord_mods = 855839522620047420
    twtv_mods = 855839453020422185
    muted = 728305872438296581
    selfmuted = 971419220728508517

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

    # alu server nonani
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

    # wink server nonani

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


class MaterialPalette(discord.Colour):
    """Material Design Color Palette"""

    def __init__(self, value: int):
        super().__init__(value)

    colors = {
        'red': [0xB71C1C, 0xC62828, 0xD32F2F, 0xE53935, 0xF44336, 0xEF5350, 0xE57373, 0xEF9A9A, 0xFFCDD2, 0xFFEBEE],
        'pink': [0x880E4F, 0xAD1457, 0xC2185B, 0xD81B60, 0xE91E63, 0xEC407A, 0xF06292, 0xF48FB1, 0xF8BBD0, 0xFCE4EC],
        'purple': [0x4A148C, 0x6A1B9A, 0x7B1FA2, 0x8E24AA, 0x9C27B0, 0xAB47BC, 0xBA68C8, 0xCE93D8, 0xE1BEE7, 0xF3E5F5],
        'deep_purple': [
            0x311B92,
            0x4527A0,
            0x512DA8,
            0x5E35B1,
            0x673AB7,
            0x7E57C2,
            0x9575CD,
            0xB39DDB,
            0xD1C4E9,
            0xEDE7F6,
        ],
        'indigo': [0x1A237E, 0x283593, 0x303F9F, 0x3949AB, 0x3F51B5, 0x5C6BC0, 0x7986CB, 0x9FA8DA, 0xC5CAE9, 0xE8EAF6],
        'blue': [0x0D47A1, 0x1565C0, 0x1976D2, 0x1E88E5, 0x2196F3, 0x42A5F5, 0x64B5F6, 0x90CAF9, 0xBBDEFB, 0xE3F2FD],
        'light_blue': [
            0x01579B,
            0x0277BD,
            0x0288D1,
            0x039BE5,
            0x03A9F4,
            0x29B6F6,
            0x4FC3F7,
            0x81D4FA,
            0xB3E5FC,
            0xE1F5FE,
        ],
        'cyan': [0x006064, 0x00838F, 0x0097A7, 0x00ACC1, 0x00BCD4, 0x26C6DA, 0x4DD0E1, 0x80DEEA, 0xB2EBF2, 0xE0F7FA],
        'teal': [0x004D40, 0x00695C, 0x00796B, 0x00897B, 0x009688, 0x26A69A, 0x4DB6AC, 0x80CBC4, 0xB2DFDB, 0xE0F2F1],
        'green': [0x1B5E20, 0x2E7D32, 0x388E3C, 0x43A047, 0x4CAF50, 0x66BB6A, 0x81C784, 0xA5D6A7, 0xC8E6C9, 0xE8F5E9],
        'light_green': [
            0x33691E,
            0x558B2F,
            0x689F38,
            0x7CB342,
            0x8BC34A,
            0x9CCC65,
            0xAED581,
            0xC5E1A5,
            0xDCEDC8,
            0xF1F8E9,
        ],
        'lime': [0x827717, 0x9E9D24, 0xAFB42B, 0xC0CA33, 0xCDDC39, 0xD4E157, 0xDCE775, 0xE6EE9C, 0xF0F4C3, 0xF9FBE7],
        'yellow': [0xF57F17, 0xF9A825, 0xFBC02D, 0xFDD835, 0xFFEB3B, 0xFFEE58, 0xFFF176, 0xFFF59D, 0xFFF9C4, 0xFFFDE7],
        'amber': [0xFF6F00, 0xFF8F00, 0xFFA000, 0xFFB300, 0xFFC107, 0xFFCA28, 0xFFD54F, 0xFFE082, 0xFFECB3, 0xFFF8E1],
        'orange': [0xE65100, 0xEF6C00, 0xF57C00, 0xFB8C00, 0xFF9800, 0xFFA726, 0xFFB74D, 0xFFCC80, 0xFFE0B2, 0xFFF3E0],
        'deep_orange': [
            0xBF360C,
            0xD84315,
            0xE64A19,
            0xF4511E,
            0xFF5722,
            0xFF7043,
            0xFF8A65,
            0xFFAB91,
            0xFFCCBC,
            0xFBE9E7,
        ],
        'brown': [0x3E2723, 0x4E342E, 0x5D4037, 0x6D4C41, 0x795548, 0x8D6E63, 0xA1887F, 0xBCAAA4, 0xD7CCC8, 0xEFEBE9],
        'gray': [0x212121, 0x424242, 0x616161, 0x757575, 0x9E9E9E, 0xBDBDBD, 0xE0E0E0, 0xEEEEEE, 0xF5F5F5, 0xFAFAFA],
        'blue_gray': [
            0x263238,
            0x37474F,
            0x455A64,
            0x546E7A,
            0x607D8B,
            0x78909C,
            0x90A4AE,
            0xB0BEC5,
            0xCFD8DC,
            0xECEFF1,
        ],
        'black': [0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000],
        'white': [0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF],
    }
    shades = [900, 800, 700, 600, 500, 400, 300, 200, 100, 50]
    core: Literal[500] = 500
    colors_dict = {}
    for key, values in colors.items():
        colors_dict[key] = {shade: clr for shade, clr in zip(shades, values)}

    ShadeTypeHint = Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50]

    @classmethod
    def red(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['red'][shade])

    @classmethod
    def pink(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['pink'][shade])

    @classmethod
    def purple(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['purple'][shade])

    @classmethod
    def deep_purple(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['deep_purple'][shade])

    @classmethod
    def indigo(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['indigo'][shade])

    @classmethod
    def blue(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['blue'][shade])

    @classmethod
    def light_blue(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['light_blue'][shade])

    @classmethod
    def cyan(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['cyan'][shade])

    @classmethod
    def teal(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['teal'][shade])

    @classmethod
    def green(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['green'][shade])

    @classmethod
    def light_green(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['light_green'][shade])

    @classmethod
    def lime(cls, *, shade: Optional[ShadeTypeHint] = core) -> Self:
        return cls(cls.colors_dict['lime'][shade])

    @classmethod
    def yellow(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['yellow'][shade])

    @classmethod
    def amber(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['amber'][shade])

    @classmethod
    def orange(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['orange'][shade])

    @classmethod
    def deep_orange(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['deep_orange'][shade])

    @classmethod
    def brown(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['brown'][shade])

    @classmethod
    def gray(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['gray'][shade])

    @classmethod
    def blue_gray(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls.colors_dict['blue_gray'][shade]

    @classmethod
    def black(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['black'][shade])

    @classmethod
    def white(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['white'][shade])


class MaterialAccentPalette(discord.Colour):
    """Material Design Color Palette with Accent Designs"""

    def __init__(self, value: int):
        super().__init__(value)

    colors = {
        'red': [0xD50000, 0xFF1744, 0xFF5252, 0xFF8A80],
        'pink': [0xC51162, 0xF50057, 0xFF4081, 0xFF80AB],
        'purple': [0xAA00FF, 0xD500F9, 0xE040FB, 0xEA80FC],
        'deep-purple': [0x6200EA, 0x651FFF, 0x7C4DFF, 0xB388FF],
        'indigo': [0x304FFE, 0x3D5AFE, 0x536DFE, 0x8C9EFF],
        'blue': [0x2962FF, 0x2979FF, 0x448AFF, 0x82B1FF],
        'light-blue': [0x0091EA, 0x00B0FF, 0x40C4FF, 0x80D8FF],
        'cyan': [0x00B8D4, 0x00E5FF, 0x18FFFF, 0x84FFFF],
        'teal': [0x00BFA5, 0x1DE9B6, 0x64FFDA, 0xA7FFEB],
        'green': [0x00C853, 0x00E676, 0x69F0AE, 0xB9F6CA],
        'light-green': [0x64DD17, 0x76FF03, 0xB2FF59, 0xCCFF90],
        'lime': [0xAEEA00, 0xC6FF00, 0xEEFF41, 0xF4FF81],
        'yellow': [0xFFD600, 0xFFEA00, 0xFFFF00, 0xFFFF8D],
        'amber': [0xFFAB00, 0xFFC400, 0xFFD740, 0xFFE57F],
        'orange': [0xFF6D00, 0xFF9100, 0xFFAB40, 0xFFD180],
        'deep-orange': [0xDD2C00, 0xFF3D00, 0xFF6E40, 0xFF9E80],
    }
    shades = [700, 400, 200, 100]
    core: Literal[200] = 200
    ShadeTypeHint = Literal[700, 400, 200, 100]

    colors_dict = {}
    for k, v in colors.items():
        colors_dict[k] = {shade: clr for shade, clr in zip(shades, v)}

    @classmethod
    def red(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['red'][shade])

    @classmethod
    def pink(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['pink'][shade])

    @classmethod
    def purple(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['purple'][shade])

    @classmethod
    def deep_purple(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['deep_purple'][shade])

    @classmethod
    def indigo(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['indigo'][shade])

    @classmethod
    def blue(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['blue'][shade])

    @classmethod
    def light_blue(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['light_blue'][shade])

    @classmethod
    def cyan(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['cyan'][shade])

    @classmethod
    def teal(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['teal'][shade])

    @classmethod
    def green(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls.colors_dict['green'][shade]

    @classmethod
    def light_green(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls.colors_dict['light_green'][shade]

    @classmethod
    def lime(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls.colors_dict['lime'][shade]

    @classmethod
    def yellow(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls.colors_dict['yellow'][shade]

    @classmethod
    def amber(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls.colors_dict['amber'][shade]

    @classmethod
    def orange(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls.colors_dict['orange'][shade]

    @classmethod
    def deep_orange(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls.colors_dict['deep_orange'][shade]

    @classmethod
    def brown(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['brown'][shade])

    @classmethod
    def gray(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['gray'][shade])

    @classmethod
    def blue_gray(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['blue_gray'][shade])

    @classmethod
    def black(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['black'][shade])

    @classmethod
    def white(cls, *, shade: ShadeTypeHint = core) -> Self:
        return cls(cls.colors_dict['white'][shade])


# aliases
MP = MaterialPalette
MAP = MaterialAccentPalette

if __name__ == '__main__':
    from PIL import Image

    rectangle = Image.new("RGB", (600, 300), str(MP.purple()))
    rectangle.show()
