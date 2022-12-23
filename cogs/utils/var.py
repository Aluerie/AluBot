from typing import TYPE_CHECKING, Literal, Optional
from typing_extensions import Self

from discord import Colour

if TYPE_CHECKING:
    pass


def cmntn(id_):
    return f'<#{id_}>'


def umntn(id_):
    return f'<@!{id_}>'


def rmntn(id_):
    return f'<@&{id_}>'


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
    url_search = r"\b((?:https?://)?(?:(?:www\.)?(?:[\da-z\.-]+)\.(?:[a-z]{2,6})|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|(?:(?:[0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(?:ffff(?::0{1,4}){0,1}:){0,1}(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])))(?::[0-9]{1,4}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])?(?:/[\w\.-]*)*/?)\b"


# todo: make it a bit better with classes heritage and stuff


class Sid:
    alu = 702561315478044804
    wink = 759916212842659850
    blush = 1015226252086476860

    guild_ids = [
        alu,
        wink,
        blush
    ]


class ChannelID(int):

    @property
    def mention(self):
        return f'<#{self}>'


class ChannelCollection:
    def __init__(self, **kwargs: int):
        self.kwargs = kwargs

    def __getattr__(self, attr: str) -> int:
        return ChannelID(self.kwargs.get(attr))

    def __repr__(self) -> str:
        return f"<Known Channels IDs {self.kwargs!r}"


Cid = ChannelCollection(
    # alu server
    rules=724996010169991198,
    roles=725941486063190076,
    welcome=725000501690630257,
    stream_notifs=724420415199379557,
    clips=770721052711845929,
    bday_notifs=748604236190842881,
    general=702561315478044807,
    emote_spam=730838697443852430,
    comfy_spam=727539910713671802,
    pubs_talk=731376390103892019,
    logs=731615128050598009,
    alubot=724991054474117241,
    saved=709028718286340106,
    confessions=731703242597072896,
    weebs=731887442768166933,
    bot_spam=724986090632642653,
    nsfw_bob_spam=731607736155897978,

    stream_room=766063288302698496,

    dota_news=724986688589267015,
    lol_news=724993871662022766,

    patch_notes=731759693113851975,
    suggestions=724994495581782076,

    my_time=788915790543323156,

    # wink server
    roses=759916212842659853,
    spam_me=970823670702411810,
    repost=971504469995049041,

    coop=966366521607745586,

    global_logs=997149550324240465,

    copylol_ff20=791099728498130944,
    copydota_info=873430376033452053,
    copydota_steam=881843565251141632,
    copydota_tweets=963954743644934184,
)


class Cids:
    blacklisted_array = []


class Uid:
    alu = 312204139751014400
    bot = 713124699663499274
    yen = 948934071432654929
    mandara = 812763204010246174
    mango = 213476188037971968
    nqn = 559426966151757824


class Rid:
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

    waste_bots_role = 1015289532645642314


class Ems:  # Emote strings
    # alu server nonani
    bedNerdge = '<:bedNerdge:855495407110586439>'
    DankApprove = '<:DankApprove:853015071042961468>'
    DankHatTooBig = '<:DankHatTooBig:855056297098215474>'
    DankFix = '<:DankFix:924285577027784774>'
    Ree = '<:Ree:735905686910664797>'
    PepoG = '<:PepoG:930335533970911262>'
    PepoBeliever = '<:PepoBeliever:730887642404618314>'
    peepoComfy = '<:peepoComfy:726438781208756288>'
    FeelsDankMan = '<:FeelsDankMan:726441255805911120>'
    PogChampPepe = '<:PogChampPepe:785600902140526642>'
    PepoDetective = '<:PepoDetective:743988423500628102>'
    peepoHappyDank = '<:peepoHappyDank:852928248953831514>'
    peepoRose = '<:peepoRose:856262331666923580>'
    PepoRules = '<:PepoRules:772399483039907860>'
    Smartge = '<:Smartge:869075184445956156>'
    peepoWave = '<:peepoHey:856262331217346571>'
    peepoBlushDank = '<:peepoBlushDank:853744336214032384>'
    peepoPlsStepOnMe = '<:peepoStepOnMePls:761174324420935722>'

    peepoPolice = '<:BASEDPOLICE:960004884235690024>'
    Jebaited = '<:Jebaited:726450170769703015>'
    peepoNiceDay = '<:peepoNiceDay:857224123885158400>'
    DankLove = '<:DankLove:773614700700368927>'

    MadgeThreat = '<:DankMadgeThreat:854318972102770728>'
    peepoWTF = '<:peepoWTF:730688500680097862>'
    DankZzz = '<:DankZzz:732126852251910144>'

    # alu server ani
    FeelsRainMan = '<a:SmogeInTheRain:902254223851421796>'
    DankL = '<a:DankL:1014616758470070353>'

    # wink server nonani

    bubuSip = '<:bubuSip:865033396189921290>'
    bubuGun = '<:bubuGun:847805078543007755>'
    bubuChrist = '<:bubuChrist:847805078769631262>'
    bubuAyaya = '<:bubuAYAYA:764835239138164756>'
    slash = '<:_:823159274954817566>'
    TwoBButt = '<:2BButt:853729747846168576>'
    Lewd = '<:Lewd:976604430059331684>'
    DankG = '<:DankG:998012133948276857>'
    peepoBusiness = '<:peepoBusiness:998157352098340934>'
    peepoMovie = '<:peepoMovie:998163742741246003>'
    # wink server ani
    # nothing for now

    # general emotes
    Offline = '🔴'
    Online = '🟢'
    # emotes arrays
    comfy_emotes = [
        "<:peepoComfy:726438781208756288>",
        "<:pepoblanket:595156413974577162>"
    ]
    phone_numbers = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '*️⃣', '#️⃣']


class Img:
    league = 'https://i.imgur.com/MtT6oKS.png'
    github = 'https://pics.freeicons.io/uploads/icons/png/4381378511600029534-512.png'
    heart = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/263/purple-heart_1f49c.png"
    dota2logo = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/global/dota2_logo_symbol.png"
    twitchtv = \
        "https://cdn3.iconfinder.com/data/icons/" \
        "social-messaging-ui-color-shapes-2-free/128/social-twitch-circle-512.png"


class Lmt:
    class Embed:
        sum_all = 6000
        footer_text = 2048
        title = 25
        description = 4096
        field_amount = 25
        field_name = 256
        field_value = 1024


class Clr:
    """My chosen colours"""
    prpl = Colour(0x9678b6)
    rspbrry = Colour(0xC42C48)
    red = Colour(0xff0000)
    neon = Colour(0x4D4DFF)
    error = Colour(0x800000)
    olive = Colour(0x98BF64)
    twitch = Colour(0x9146FF)


class MaterialPalette(Colour):
    """Material Design Color Palette"""

    def __init__(self, value: int):
        super().__init__(value)

    colors = {
        'red': [
            0xb71c1c, 0xc62828, 0xd32f2f, 0xe53935, 0xf44336,
            0xef5350, 0xe57373, 0xef9a9a, 0xffcdd2, 0xffebee
        ],
        'pink': [
            0x880e4f, 0xad1457, 0xc2185b, 0xd81b60, 0xe91e63,
            0xec407a, 0xf06292, 0xf48fb1, 0xf8bbd0, 0xfce4ec
        ],
        'purple': [
            0x4a148c, 0x6a1b9a, 0x7b1fa2, 0x8e24aa, 0x9c27b0,
            0xab47bc, 0xba68c8, 0xce93d8, 0xe1bee7, 0xf3e5f5
        ],
        'deep_purple': [
            0x311b92, 0x4527a0, 0x512da8, 0x5e35b1, 0x673ab7,
            0x7e57c2, 0x9575cd, 0xb39ddb, 0xd1c4e9, 0xede7f6
        ],
        'indigo': [
            0x1a237e, 0x283593, 0x303f9f, 0x3949ab, 0x3f51b5,
            0x5c6bc0, 0x7986cb, 0x9fa8da, 0xc5cae9, 0xe8eaf6
        ],
        'blue': [
            0x0d47a1, 0x1565c0, 0x1976d2, 0x1e88e5, 0x2196f3,
            0x42a5f5, 0x64b5f6, 0x90caf9, 0xbbdefb, 0xe3f2fd
        ],
        'light_blue': [
            0x01579b, 0x0277bd, 0x0288d1, 0x039be5, 0x03a9f4,
            0x29b6f6, 0x4fc3f7, 0x81d4fa, 0xb3e5fc, 0xe1f5fe
        ],
        'cyan': [
            0x006064, 0x00838f, 0x0097a7, 0x00acc1, 0x00bcd4,
            0x26c6da, 0x4dd0e1, 0x80deea, 0xb2ebf2, 0xe0f7fa
        ],
        'teal': [
            0x004d40, 0x00695c, 0x00796b, 0x00897b, 0x009688,
            0x26a69a, 0x4db6ac, 0x80cbc4, 0xb2dfdb, 0xe0f2f1
        ],
        'green': [
            0x1b5e20, 0x2e7d32, 0x388e3c, 0x43a047, 0x4caf50,
            0x66bb6a, 0x81c784, 0xa5d6a7, 0xc8e6c9, 0xe8f5e9
        ],
        'light_green': [
            0x33691e, 0x558b2f, 0x689f38, 0x7cb342, 0x8bc34a,
            0x9ccc65, 0xaed581, 0xc5e1a5, 0xdcedc8, 0xf1f8e9
        ],
        'lime': [
            0x827717, 0x9e9d24, 0xafb42b, 0xc0ca33, 0xcddc39,
            0xd4e157, 0xdce775, 0xe6ee9c, 0xf0f4c3, 0xf9fbe7
        ],
        'yellow': [
            0xf57f17, 0xf9a825, 0xfbc02d, 0xfdd835, 0xffeb3b,
            0xffee58, 0xfff176, 0xfff59d, 0xfff9c4, 0xfffde7
        ],
        'amber': [
            0xff6f00, 0xff8f00, 0xffa000, 0xffb300, 0xffc107,
            0xffca28, 0xffd54f, 0xffe082, 0xffecb3, 0xfff8e1
        ],
        'orange': [
            0xe65100, 0xef6c00, 0xf57c00, 0xfb8c00, 0xff9800,
            0xffa726, 0xffb74d, 0xffcc80, 0xffe0b2, 0xfff3e0
        ],
        'deep_orange': [
            0xbf360c, 0xd84315, 0xe64a19, 0xf4511e, 0xff5722,
            0xff7043, 0xff8a65, 0xffab91, 0xffccbc, 0xfbe9e7
        ],
        'brown': [
            0x3e2723, 0x4e342e, 0x5d4037, 0x6d4c41, 0x795548,
            0x8d6e63, 0xa1887f, 0xbcaaa4, 0xd7ccc8, 0xefebe9
        ],
        'gray': [
            0x212121, 0x424242, 0x616161, 0x757575, 0x9e9e9e,
            0xbdbdbd, 0xe0e0e0, 0xeeeeee, 0xf5f5f5, 0xfafafa
        ],
        'blue_gray': [
            0x263238, 0x37474f, 0x455a64, 0x546e7a, 0x607d8b,
            0x78909c, 0x90a4ae, 0xb0bec5, 0xcfd8dc, 0xeceff1
        ],
        'black': [
            0x000000, 0x000000, 0x000000, 0x000000, 0x000000,
            0x000000, 0x000000, 0x000000, 0x000000, 0x000000
        ],
        'white': [
            0xffffff, 0xffffff, 0xffffff, 0xffffff, 0xffffff,
            0xffffff, 0xffffff, 0xffffff, 0xffffff, 0xffffff
        ]
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


class MaterialAccentPalette(Colour):
    """Material Design Color Palette with Accent Designs"""

    def __init__(self, value: int):
        super().__init__(value)

    colors = {
        'red': [
            0xd50000, 0xff1744, 0xff5252, 0xff8a80
        ],
        'pink': [
            0xc51162, 0xf50057, 0xff4081, 0xff80ab
        ],
        'purple': [
            0xaa00ff, 0xd500f9, 0xe040fb, 0xea80fc
        ],
        'deep-purple': [
            0x6200ea, 0x651fff, 0x7c4dff, 0xb388ff
        ],
        'indigo': [
            0x304ffe, 0x3d5afe, 0x536dfe, 0x8c9eff
        ],
        'blue': [
            0x2962ff, 0x2979ff, 0x448aff, 0x82b1ff
        ],
        'light-blue': [
            0x0091ea, 0x00b0ff, 0x40c4ff, 0x80d8ff
        ],
        'cyan': [
            0x00b8d4, 0x00e5ff, 0x18ffff, 0x84ffff
        ],
        'teal': [
            0x00bfa5, 0x1de9b6, 0x64ffda, 0xa7ffeb
        ],
        'green': [
            0x00c853, 0x00e676, 0x69f0ae, 0xb9f6ca
        ],
        'light-green': [
            0x64dd17, 0x76ff03, 0xb2ff59, 0xccff90
        ],
        'lime': [
            0xaeea00, 0xc6ff00, 0xeeff41, 0xf4ff81
        ],
        'yellow': [
            0xffd600, 0xffea00, 0xffff00, 0xffff8d
        ],
        'amber': [
            0xffab00, 0xffc400, 0xffd740, 0xffe57f
        ],
        'orange': [
            0xff6d00, 0xff9100, 0xffab40, 0xffd180
        ],
        'deep-orange': [
            0xdd2c00, 0xff3d00, 0xff6e40, 0xff9e80
        ]
    }
    shades = [700, 400, 200, 100]
    core: Literal[200] = 200

    colors_dict = {}
    for k, v in colors.items():
        colors_dict[k] = {shade: clr for shade, clr in zip(shades, v)}

    ShadeTypeHint = Literal[700, 400, 200, 100]

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
