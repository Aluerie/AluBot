def cmntn(id_):
    return f'<#{id_}>'


def umntn(id_):
    return f'<@!{id_}>'


def rmntn(id_):
    return f'<@&{id_}>'


class Rgx:
    whitespaces = "\s"  # whitespaces
    emote = "<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"  # emotes
    nqn = ":(?P<name>[a-zA-Z0-9_]{2,32}):"  # standard emotes
    # emoji = get_emoji_regexp() # use from emoji import get_emoji_regexp for this
    bug_check = ":.*:"
    emote_stats = r"<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>"
    emote_stats_ids = r"<a?:[a-zA-Z0-9_]{2,32}:([0-9]{18,22})>"
    invis_symb = "[^!-~]+"  # idk might be huge question mark

    url_danny = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    url_simple = r"(https?://\S+)"
    url_search = r"\b((?:https?://)?(?:(?:www\.)?(?:[\da-z\.-]+)\.(?:[a-z]{2,6})|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|(?:(?:[0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(?:ffff(?::0{1,4}){0,1}:){0,1}(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])))(?::[0-9]{1,4}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])?(?:/[\w\.-]*)*/?)\b"


class Sid:
    irene = 702561315478044804
    emote = 759916212842659850

    guild_ids = [
        irene,
        emote,
    ]


class Cid:
    # irene server
    rules = 724996010169991198
    roles = 725941486063190076

    welcome = 725000501690630257
    stream_notifs = 724420415199379557
    clips = 770721052711845929
    bday_notifs = 748604236190842881

    general = 702561315478044807
    emote_spam = 730838697443852430
    comfy_spam = 727539910713671802
    pubs_talk = 731376390103892019
    logs = 731615128050598009
    irene_bot = 724991054474117241
    saved = 709028718286340106
    confessions = 731703242597072896
    weebs = 731887442768166933
    bot_spam = 724986090632642653
    nsfw_bob_spam = 731607736155897978

    text_for_vc = 761473270641328130
    stream_room = 766063288302698496

    dota_news = 724986688589267015
    lol_news = 724993871662022766

    patch_notes = 731759693113851975
    suggestions = 724994495581782076

    my_time = 788915790543323156

    blacklisted_array = [ ]
    # emote server
    spam_me = 970823670702411810

    copylol_ff20 = 791099728498130944
    copydota_info = 873430376033452053
    copydota_steam = 881843565251141632
    copydota_tweets = 963954743644934184


class Uid:
    irene = 312204139751014400
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
    subs = 706538741782675616
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

    level_zero = 852663921085251585
    category_roles_ids = [
        856589983707693087,  # moderation
        852199351808032788,  # activity
        852193537067843634,  # subscription
        852199851840372847,  # special
        851786344354938880,  # games
        852192240306618419,  # notification
        852194400922632262,  # pronoun
        plebs,               # plebs
    ]
    level_roles = [] # maybe fill it later
    ignored_for_logs = [voice, live_stream] + category_roles_ids


class Ems: #Emote strings
    # irene server nonani
    DankApprove = '<:DankApprove:853015071042961468>'
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

    peepoPolice = '<:BASEDPOLICE:960004884235690024>'
    Jebaited = '<:Jebaited:726450170769703015>'
    peepoNiceDay = '<:peepoNiceDay:857224123885158400>'
    peepoLove = '<:DankLove:773614700700368927>'

    MadgeThreat = '<:MadgeThreat:772398923300995082>'
    peepoWTF = '<:peepoWTF:730688500680097862>'

    # irene server ani
    FeelsRainMan = '<a:SmogeInTheRain:902254223851421796>'

    # emote server nonani

    bubuSip = '<:bubuSip:865033396189921290>'
    bubuGun = '<:bubuGun:847805078543007755>'
    bubuChrist = '<:bubuChrist:847805078769631262>'
    bubuAyaya = '<:bubuAYAYA:764835239138164756>'
    slash = '<:slash:823159274954817566>'
    TwoBButt = '<:2BButt:853729747846168576>'

    # emote server ani
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


class Clr:
    prpl = 0x9678b6
    rspbrry = 0xC42C48
    wht = 0xffffff
    red = 0xff0000
    neon = 0x4D4DFF
    error = 0x800000
    dota_colour_map = {
        0: "#3375FF", 1: "#66FFBF", 2: "#BF00BF", 3: "#F3F00B", 4: "#FF6B00",
        5: "#FE86C2", 6: "#A1B447", 7: "#65D9F7", 8: "#008321", 9: "#A46900"
    }


class Img:
    heart = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/263/purple-heart_1f49c.png"
    dota2logo = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/global/dota2_logo_symbol.png"
    twitchtv = "https://cdn3.iconfinder.com/data/icons/social-messaging-ui-color-shapes-2-free/128/social-twitch-circle-512.png"
