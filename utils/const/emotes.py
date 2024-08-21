from enum import StrEnum

from ._meta import CONSTANTS

# emote names should match discord ones and etc thus:
# ruff: noqa: N815


class Emote(StrEnum):
    """Emote strings.

    Names should match namings for discord emotes they represent.
    """

    # comments mean that this emote is used in help command for something so i don't reuse it by accident

    #########################################
    # COMMUNITY SERVER, NON-ANIMATED EMOTES #
    #########################################
    peepoComfy = "<:_:726438781208756288>"  # Category: Community
    UpvoteSuggestion = "<:DankApprove:853015071042961468>"  # it has to be from the community guild itself

    ##################
    # Emote Server 1 #
    ##################

    # non animated
    DankApprove = "<:DankApprove:1125591734332706907>"
    DankFix = "<:DankFix:1125591737939791963>"  # Category: Jishaku
    DankG = "<:DankG:1125591639256211596>"
    DankHatTooBig = "<:DankHatTooBig:1125591656192806922>"
    DankHey = "<:DankHey:1125591893871448095>"
    DankLove = "<:DankLove:1125591725931515976>"
    DankMadgeThreat = "<:DankMadgeThreat:1125591898241892482>"
    DankZzz = "<:DankZzz:1125591722487984208>"
    FeelsDankMan = "<:FeelsDankMan:1125591801785503884>"
    FeelsDankManLostHisHat = "<:FeelsDankManLostHisHat:1125591840427618384>"
    Jebaited = "<:Jebaited:1125591730163552328>"  # Category: Jebaited
    Lewd = "<:Lewd:1125591635296796792>"
    PepoBeliever = "<:PepoBeliever:1125591746265501716>"
    PepoDetective = "<:PepoDetective:1125591814188044298>"
    PepoG = "<:PepoG:1125591718373371914>"
    PepoRules = "<:PepoRules:1125591823348416542>"
    PogChampPepe = "<:PogChampPepe:1125591805363236934>"
    Ree = "<:Ree:1125591742712918146>"
    Smartge = "<:Smartge:1125591827425263617>"
    WeebsOut = "<:WeebsOut:1125598043455115264>"
    bedNerdge = "<:bedNerdge:1125591713386352692>"
    bedWTF = "<:bedWTF:1125591651495194694>"  # Category: Beta
    bubuAYAYA = "<:bubuAYAYA:1125591624710357013>"
    bubuChrist = "<:bubuChrist:1125591632268496979>"
    bubuGun = "<:bubuGun:1125591628996948048>"
    peepoBlushDank = "<:peepoBlushDank:1125591832240328786>"
    peepoBusiness = "<:peepoBusiness:1125591642729091113>"
    # peepoComfy = '<:peepoComfy:1125591750665318420>' # we will use the one from community
    peepoHappyDank = "<:peepoHappyDank:1125591819137335304>"
    peepoMovie = "<:peepoMovie:1125591645853859901>"
    peepoNiceDay = "<:peepoNiceDay:1125591903488987236>"
    peepoPolice = "<:peepoPolice:1125591845540462693>"
    peepoRiot = "<:peepoRiot:1125597699778035713>"
    peepoRoseDank = "<:peepoRoseDank:1125591890037854299>"
    peepoStepOnMePls = "<:peepoStepOnMePls:1125591836057145396>"
    peepoWater = "<:peepoWater:1125720123722973285>"
    peepoWTF = "<:peepoWTF:1125591659846058035>"
    peepoRedCard = "<:peepoRedCard:1139905850077626399>"
    peepoYellowCard = "<:peepoYellowCard:1139908316508729436>"

    # animated
    DankL = "<a:DankL:1125591914524184667>"
    KURU = "<a:KURU:1125591919574138940>"
    SmogeInTheRain = "<a:SmogeInTheRain:1125591908656361574>"
    WeebsOutOut = "<a:WeebsOutOut:1125597169957748826>"
    peepoWeebSmash = "<a:peepoWeebSmash:1125597172675653662>"

    #################
    # COMMON EMOTES #
    #################

    Offline = "\N{LARGE RED CIRCLE}"
    Online = "\N{LARGE GREEN CIRCLE}"


class Tick(StrEnum):
    """Tick StrEnum, used to match True/False with yes/no emotes."""

    Yes = "\N{WHITE HEAVY CHECK MARK}"
    No = "\N{CROSS MARK}"
    Black = "\N{BLACK LARGE SQUARE}"


DIGITS = [
    "\N{DIGIT ZERO}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT SIX}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT SEVEN}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT EIGHT}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT NINE}\N{COMBINING ENCLOSING KEYCAP}",
]


class GitIssueEvent(StrEnum):
    """Emotes to showcase GitHub Issue Events with."""

    # pictures are taken from 16px versions here https://primer.style/octicons/
    # and background circles are added with a simple online editor https://iconscout.com/color-editor
    # make pics to be 128x128, so it's consistent for all sizes
    # =========================================================
    # Emotes from B1-50 extra emote server, names match GitHub event names (and emote names)
    # events
    reopened = "<:reopened:1125588760269164587>"
    opened = "<:opened:1125588763087753307>"
    closed = "<:closed:1125588765759508552>"
    # comments
    assigned = "<:assigned:1125588768070578196>"
    commented = "<:commented:1125588770679431258>"


class EmoteLogo(StrEnum):
    """Emotes to showcase some logos with."""

    # Emotes from BXX extra emote servers, names match emote names in those servers (try to keep them PascalCase)
    GitHub = "<:GitHub:1125588758197178439>"
    AluerieServer = "<:AluerieServer:1125600089109442661>"


DOTA_HERO_EMOTES: dict[int, str] = {
    # mapping dota hero ids to their correlated hero-icon emotes.
    # TODO: upload all these emotes into the Discord DEV portal new app emotes tab.
    # TODO: rename all emotes to Pascal Case but with underscores :D
    1: "<:antimage:1202019770787176529>",
    2: "<:axe:1202019772997304471>",
    3: "<:bane:1202019775291592754>",
    4: "<:bloodseeker:1202019777212858398>",
    5: "<:crystal_maiden:1202019779745947749>",
    6: "<:drow_ranger:1202019782556385330>",
    7: "<:earthshaker:1202019784766529596>",
    8: "<:juggernaut:1202019787698614403>",
    9: "<:mirana:1202019790080987166>",
    10: "<:morphling:1202019792429797459>",
    11: "<:nevermore:1202019795319672952>",
    12: "<:phantom_lancer:1202019797764931584>",
    13: "<:puck:1202019799694315522>",
    14: "<:pudge:1202019802378674186>",
    15: "<:razor:1202019804886863872>",
    16: "<:sand_king:1202019806602076311>",
    17: "<:storm_spirit:1202019809710047314>",
    18: "<:sven:1202019812310786130>",
    19: "<:tiny:1202019815028703254>",
    20: "<:vengefulspirit:1202019817746616362>",
    21: "<:windrunner:1202019820510388244>",
    22: "<:zuus:1202019823018573934>",
    23: "<:kunkka:1202019825690615819>",
    25: "<:lina:1202019828496601142>",
    26: "<:lion:1202019832078274601>",
    27: "<:shadow_shaman:1202019834465095691>",
    28: "<:slardar:1202019837316960339>",
    29: "<:tidehunter:1202019839422496800>",
    30: "<:witch_doctor:1202019842673086505>",
    31: "<:lich:1202019845265444917>",
    32: "<:riki:1202019847672975380>",
    33: "<:enigma:1202019850034348124>",
    34: "<:tinker:1202019851779182682>",
    35: "<:sniper:1202019854266142740>",
    36: "<:necrolyte:1202019856929525811>",
    37: "<:warlock:1202019859529998401>",
    38: "<:beastmaster:1202019862655008819>",
    39: "<:queenofpain:1202019865146437763>",
    40: "<:venomancer:1202019867822411856>",
    41: "<:faceless_void:1202019870347108462>",
    42: "<:skeleton_king:1202019873119535214>",
    43: "<:death_prophet:1202019875355103245>",
    44: "<:phantom_assassin:1202019878052319244>",
    45: "<:pugna:1202019880648577134>",
    46: "<:templar_assassin:1202019882590539816>",
    47: "<:viper:1202019885106860092>",
    48: "<:luna:1202019886906495006>",
    # guild 2
    49: "<:dragon_knight:1202026697818636339>",
    50: "<:dazzle:1202026700301668352>",
    51: "<:rattletrap:1202026703204122664>",
    52: "<:leshrac:1202026706337013851>",
    53: "<:furion:1202026709134610452>",
    54: "<:life_stealer:1202026711508860978>",
    55: "<:dark_seer:1202026713345958019>",
    56: "<:clinkz:1202026715694768218>",
    57: "<:omniknight:1202026718211088437>",
    58: "<:enchantress:1202026720388186204>",
    59: "<:huskar:1202026723441381476>",
    60: "<:night_stalker:1202026726075674645>",
    61: "<:broodmother:1202026728625807361>",
    62: "<:bounty_hunter:1202026732383907940>",
    63: "<:weaver:1202026735072460831>",
    64: "<:jakiro:1202026737572249630>",
    65: "<:batrider:1202026739275153521>",
    66: "<:chen:1202026741854642297>",
    67: "<:spectre:1202026744207376386>",
    68: "<:ancient_apparition:1202026746791333898>",
    69: "<:doom_bringer:1202026750511423488>",
    70: "<:ursa:1202026752776622132>",
    71: "<:spirit_breaker:1202026755595194398>",
    72: "<:gyrocopter:1202026758132465744>",
    73: "<:alchemist:1202026760607109232>",
    74: "<:invoker:1202026763291730000>",
    75: "<:silencer:1202026765791547422>",
    76: "<:obsidian_destroyer:1202026767863533568>",
    77: "<:lycan:1202026770031706184>",
    78: "<:brewmaster:1202026772653408297>",
    79: "<:shadow_demon:1202026775412998214>",
    80: "<:lone_druid:1202026778282168341>",
    81: "<:chaos_knight:1202026781033644112>",
    82: "<:meepo:1202026783650893855>",
    83: "<:treant:1202026786188443718>",
    84: "<:ogre_magi:1202026788486909982>",
    85: "<:undying:1202026790932205672>",
    # guild 3
    86: "<:rubick:1202027073464717373>",
    87: "<:disruptor:1202027076316565575>",
    88: "<:nyx_assassin:1202027079475150898>",
    89: "<:naga_siren:1202027082058838117>",
    90: "<:keeper_of_the_light:1202029134101106718>",
    91: "<:wisp:1202029137280114760>",
    92: "<:visage:1202029140811984918>",
    93: "<:slark:1202029143190155304>",
    94: "<:medusa:1202029145563861012>",
    95: "<:troll_warlord:1202029147937833000>",
    96: "<:centaur:1202029150282719283>",
    97: "<:magnataur:1202029152694440029>",
    98: "<:shredder:1202029155366215752>",
    99: "<:bristleback:1202029157710823464>",
    100: "<:tusk:1202029160072220692>",
    101: "<:skywrath_mage:1202029162408464404>",
    102: "<:abaddon:1202029164312674396>",
    103: "<:elder_titan:1202029166044917791>",
    104: "<:legion_commander:1202029169152892928>",
    105: "<:techies:1202029171480731682>",
    106: "<:ember_spirit:1202029174156427284>",
    107: "<:earth_spirit:1202029176711041035>",
    108: "<:abyssal_underlord:1202029179567358022>",
    109: "<:terrorblade:1202029182381723740>",
    110: "<:phoenix:1202029184621219920>",
    111: "<:oracle:1202029187024556042>",
    112: "<:winter_wyvern:1202029189595922492>",
    113: "<:arc_warden:1202029192255119402>",
    114: "<:monkey_king:1202029194666582087>",
    119: "<:dark_willow:1202029197061787718>",
    120: "<:pangolier:1202029199636824125>",
    121: "<:grimstroke:1202029202031779841>",
    123: "<:hoodwink:1202029204506693685>",
    126: "<:void_spirit:1202029206469623841>",
    128: "<:snapfire:1202029208574890017>",
    129: "<:mars:1202029210567446558>",
    135: "<:dawnbreaker:1202029213549592586>",
    136: "<:marci:1202029215982293003>",
    137: "<:primal_beast:1202029218167529502>",
    138: "<:muerta:1202029220616994926>",
}

LOL_CHAMPION_EMOTES: dict[int, str] = {
    # Mapping league champion ids to their correlated icon emotes.
    # guild 1
    1: "<:Annie:1202057409225556058>",
    2: "<:Olaf:1202057410974601226>",
    3: "<:Galio:1202057413017211010>",
    4: "<:TwistedFate:1202057414615248926>",
    5: "<:XinZhao:1202057416573718568>",
    6: "<:Urgot:1202057418935382057>",
    7: "<:Leblanc:1202057421275529266>",
    8: "<:Vladimir:1202057423175819284>",
    9: "<:FiddleSticks:1202057424497016914>",
    10: "<:Kayle:1202057426392850443>",
    11: "<:MasterYi:1202057428800114778>",
    12: "<:Alistar:1202057431014711318>",
    13: "<:Ryze:1202057433128632340>",
    14: "<:Sion:1202057434697568316>",
    15: "<:Sivir:1202057436773490729>",
    16: "<:Soraka:1202057439072223232>",
    17: "<:Teemo:1202057441001349151>",
    18: "<:Tristana:1202057442800971816>",
    19: "<:Warwick:1202057444398997644>",
    20: "<:Nunu:1202057446261002250>",
    21: "<:MissFortune:1202057448215822406>",
    22: "<:Ashe:1202057450170368072>",
    23: "<:Tryndamere:1202057452280107049>",
    24: "<:Jax:1202057454016266301>",
    25: "<:Morgana:1202057455715225600>",
    26: "<:Zilean:1202057457371717646>",
    27: "<:Singed:1202057460635148368>",
    28: "<:Evelynn:1202057467094368287>",
    29: "<:Twitch:1202057469267030057>",
    30: "<:Karthus:1202057471414501516>",
    31: "<:Chogath:1202057473088036894>",
    32: "<:Amumu:1202057474509914174>",
    33: "<:Rammus:1202057476191559681>",
    34: "<:Anivia:1202057478263799829>",
    35: "<:Shaco:1202057479660507208>",
    36: "<:DrMundo:1202057482135162961>",
    37: "<:Sona:1202057483921915996>",
    38: "<:Kassadin:1202057485540655104>",
    39: "<:Irelia:1202057487545806918>",
    40: "<:Janna:1202057489869439116>",
    41: "<:Gangplank:1202057491991756890>",
    42: "<:Corki:1202057493740519556>",
    43: "<:Karma:1202057496030617610>",
    44: "<:Taric:1202057498090291240>",
    45: "<:Veigar:1202057499898028114>",
    48: "<:Trundle:1202057501730934784>",
    50: "<:Swain:1202057504079740978>",
    51: "<:Caitlyn:1202057505845288991>",
    53: "<:Blitzcrank:1202057507661684737>",
    54: "<:Malphite:1202057509553045535>",
    # guild 2
    55: "<:Katarina:1202057955202039849>",
    56: "<:Nocturne:1202057957379145778>",
    57: "<:Maokai:1202057959291768903>",
    58: "<:Renekton:1202057961112092733>",
    59: "<:JarvanIV:1202057962886275132>",
    60: "<:Elise:1202057964622721035>",
    61: "<:Orianna:1202057966631800912>",
    62: "<:MonkeyKing:1202057968296927274>",
    63: "<:Brand:1202057969991426059>",
    64: "<:LeeSin:1202057972222533662>",
    67: "<:Vayne:1202057973988601886>",
    68: "<:Rumble:1202057975871840277>",
    69: "<:Cassiopeia:1202057977373134939>",
    72: "<:Skarner:1202057979395063890>",
    74: "<:Heimerdinger:1202057981324443672>",
    75: "<:Nasus:1202057983505469570>",
    76: "<:Nidalee:1202057985434861588>",
    77: "<:Udyr:1202057987351380041>",
    78: "<:Poppy:1202057989180379166>",
    79: "<:Gragas:1202057990417690656>",
    80: "<:Pantheon:1202057992305127444>",
    81: "<:Ezreal:1202057993844162651>",
    82: "<:Mordekaiser:1202057995542863956>",
    83: "<:Yorick:1202057997438947389>",
    84: "<:Akali:1202058000001675294>",
    85: "<:Kennen:1202058001872068618>",
    86: "<:Garen:1202058003621363792>",
    89: "<:Leona:1202058005227511879>",
    90: "<:Malzahar:1202058006901309481>",
    91: "<:Talon:1202058008633561138>",
    92: "<:Riven:1202058010319396895>",
    96: "<:KogMaw:1202058011611238442>",
    98: "<:Shen:1202058014006186006>",
    99: "<:Lux:1202058016426299482>",
    101: "<:Xerath:1202058017970069505>",
    102: "<:Shyvana:1202058020000116767>",
    103: "<:Ahri:1202058021778501642>",
    104: "<:Graves:1202058023460143117>",
    105: "<:Fizz:1202058025226219590>",
    106: "<:Volibear:1202058027063320597>",
    107: "<:Rengar:1202058028925321266>",
    110: "<:Varus:1202058030749847642>",
    111: "<:Nautilus:1202058032767586385>",
    112: "<:Viktor:1202058034252361770>",
    113: "<:Sejuani:1202058036013695026>",
    114: "<:Fiora:1202058037737816174>",
    115: "<:Ziggs:1202058039146844282>",
    117: "<:Lulu:1202058040640286783>",
    119: "<:Draven:1202058042557087805>",
    120: "<:Hecarim:1202058045178531890>",
    121: "<:Khazix:1202062305215660052>",
    # guild 3
    122: "<:Darius:1202062307211870220>",
    126: "<:Jayce:1202062309686792242>",
    127: "<:Lissandra:1202062311313903637>",
    131: "<:Diana:1202062313344225281>",
    133: "<:Quinn:1202062315823058964>",
    134: "<:Syndra:1202062317429469206>",
    136: "<:AurelionSol:1202062320386449408>",
    141: "<:Kayn:1202062322970140734>",
    142: "<:Zoe:1202062325297975336>",
    143: "<:Zyra:1202062327533273118>",
    145: "<:Kaisa:1202062329743679518>",
    147: "<:Seraphine:1202062333497839616>",
    150: "<:Gnar:1202062335855038534>",
    154: "<:Zac:1202062338425884702>",
    157: "<:Yasuo:1202062340770766869>",
    161: "<:Velkoz:1202062346994851923>",
    163: "<:Taliyah:1202062349557571584>",
    164: "<:Camille:1202062351558254633>",
    166: "<:Akshan:1202062353265328211>",
    200: "<:Belveth:1202062355455029278>",
    201: "<:Braum:1202062357690601482>",
    202: "<:Jhin:1202062364489293876>",
    203: "<:Kindred:1202062366498627604>",
    221: "<:Zeri:1202062368348311602>",
    222: "<:Jinx:1202062370420039732>",
    223: "<:TahmKench:1202062372962045962>",
    233: "<:Briar:1202062375684165703>",
    234: "<:Viego:1202062378162978818>",
    235: "<:Senna:1202062380780224572>",
    236: "<:Lucian:1202062383368110121>",
    238: "<:Zed:1202062386140549150>",
    240: "<:Kled:1202062388522655754>",
    245: "<:Ekko:1202062391148552263>",
    246: "<:Qiyana:1202062393115410513>",
    254: "<:Vi:1202062395510362183>",
    266: "<:Aatrox:1202062397674889248>",
    267: "<:Nami:1202062399956586526>",
    268: "<:Azir:1202062402053738536>",
    350: "<:Yuumi:1202062403827667025>",
    360: "<:Samira:1202062406143193188>",
    412: "<:Thresh:1202062413193543722>",
    420: "<:Illaoi:1202062415576191037>",
    421: "<:RekSai:1202062417610412103>",
    427: "<:Ivern:1202062419535605760>",
    429: "<:Kalista:1202062421846667355>",
    432: "<:Bard:1202062423960596512>",
    497: "<:Rakan:1202062425676070913>",
    498: "<:Xayah:1202062428821524520>",
    516: "<:Ornn:1202062431229313125>",
    # guild 4
    517: "<:Sylas:1202062805549973535>",
    518: "<:Neeko:1202062807781343264>",
    523: "<:Aphelios:1202062809819779122>",
    526: "<:Rell:1202062811795300353>",
    555: "<:Pyke:1202062814164815884>",
    711: "<:Vex:1202062815847006239>",
    777: "<:Yone:1202062818543665163>",
    875: "<:Sett:1202062821089615963>",
    876: "<:Lillia:1202062823706853389>",
    887: "<:Gwen:1202062826005336116>",
    888: "<:Renata:1202062828308004914>",
    895: "<:Nilah:1202062830220881920>",
    897: "<:KSante:1202062832531677225>",
    901: "<:Smolder:1202062834830426132>",
    902: "<:Milio:1202062837296406569>",
    910: "<:Hwei:1202062839142170654>",
    950: "<:Naafiri:1202062841096704050>",
}
