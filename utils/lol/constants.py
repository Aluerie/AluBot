from __future__ import annotations

from utils.const import ImageAsset

__all__ = (
    "LoLAsset",
    "CHAMPION_EMOTES",
    "NEW_CHAMPION_EMOTE",
)

_IMAGE_DIR = "./assets/images/lol/"


class LoLAsset(ImageAsset):
    ItemUnknown = f"{_IMAGE_DIR}item_unknown_64x64.png"
    RuneUnknown = f"{_IMAGE_DIR}rune_unknown_64x64.png"
    SummonerSpellUnknown = f"{_IMAGE_DIR}summoner_spell_unknown_64x64.png"


CHAMPION_EMOTES: dict[int, str] = {
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

NEW_CHAMPION_EMOTE = "\N{SQUARED NEW}"