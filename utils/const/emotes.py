from enum import StrEnum


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
    """Tick StrEnum, used to match True/False with yes/no emotes"""

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


class DotaHeroes(StrEnum):
    # guild 1
    antimage = "<:antimage:1202019770787176529>"
    axe = "<:axe:1202019772997304471>"
    bane = "<:bane:1202019775291592754>"
    bloodseeker = "<:bloodseeker:1202019777212858398>"
    crystal_maiden = "<:crystal_maiden:1202019779745947749>"
    drow_ranger = "<:drow_ranger:1202019782556385330>"
    earthshaker = "<:earthshaker:1202019784766529596>"
    juggernaut = "<:juggernaut:1202019787698614403>"
    mirana = "<:mirana:1202019790080987166>"
    morphling = "<:morphling:1202019792429797459>"
    nevermore = "<:nevermore:1202019795319672952>"
    phantom_lancer = "<:phantom_lancer:1202019797764931584>"
    puck = "<:puck:1202019799694315522>"
    pudge = "<:pudge:1202019802378674186>"
    razor = "<:razor:1202019804886863872>"
    sand_king = "<:sand_king:1202019806602076311>"
    storm_spirit = "<:storm_spirit:1202019809710047314>"
    sven = "<:sven:1202019812310786130>"
    tiny = "<:tiny:1202019815028703254>"
    vengefulspirit = "<:vengefulspirit:1202019817746616362>"
    windrunner = "<:windrunner:1202019820510388244>"
    zuus = "<:zuus:1202019823018573934>"
    kunkka = "<:kunkka:1202019825690615819>"
    lina = "<:lina:1202019828496601142>"
    lion = "<:lion:1202019832078274601>"
    shadow_shaman = "<:shadow_shaman:1202019834465095691>"
    slardar = "<:slardar:1202019837316960339>"
    tidehunter = "<:tidehunter:1202019839422496800>"
    witch_doctor = "<:witch_doctor:1202019842673086505>"
    lich = "<:lich:1202019845265444917>"
    riki = "<:riki:1202019847672975380>"
    enigma = "<:enigma:1202019850034348124>"
    tinker = "<:tinker:1202019851779182682>"
    sniper = "<:sniper:1202019854266142740>"
    necrolyte = "<:necrolyte:1202019856929525811>"
    warlock = "<:warlock:1202019859529998401>"
    beastmaster = "<:beastmaster:1202019862655008819>"
    queenofpain = "<:queenofpain:1202019865146437763>"
    venomancer = "<:venomancer:1202019867822411856>"
    faceless_void = "<:faceless_void:1202019870347108462>"
    skeleton_king = "<:skeleton_king:1202019873119535214>"
    death_prophet = "<:death_prophet:1202019875355103245>"
    phantom_assassin = "<:phantom_assassin:1202019878052319244>"
    pugna = "<:pugna:1202019880648577134>"
    templar_assassin = "<:templar_assassin:1202019882590539816>"
    viper = "<:viper:1202019885106860092>"
    luna = "<:luna:1202019886906495006>"
    # guild 2
    dragon_knight = "<:dragon_knight:1202026697818636339>"
    dazzle = "<:dazzle:1202026700301668352>"
    rattletrap = "<:rattletrap:1202026703204122664>"
    leshrac = "<:leshrac:1202026706337013851>"
    furion = "<:furion:1202026709134610452>"
    life_stealer = "<:life_stealer:1202026711508860978>"
    dark_seer = "<:dark_seer:1202026713345958019>"
    clinkz = "<:clinkz:1202026715694768218>"
    omniknight = "<:omniknight:1202026718211088437>"
    enchantress = "<:enchantress:1202026720388186204>"
    huskar = "<:huskar:1202026723441381476>"
    night_stalker = "<:night_stalker:1202026726075674645>"
    broodmother = "<:broodmother:1202026728625807361>"
    bounty_hunter = "<:bounty_hunter:1202026732383907940>"
    weaver = "<:weaver:1202026735072460831>"
    jakiro = "<:jakiro:1202026737572249630>"
    batrider = "<:batrider:1202026739275153521>"
    chen = "<:chen:1202026741854642297>"
    spectre = "<:spectre:1202026744207376386>"
    ancient_apparition = "<:ancient_apparition:1202026746791333898>"
    doom_bringer = "<:doom_bringer:1202026750511423488>"
    ursa = "<:ursa:1202026752776622132>"
    spirit_breaker = "<:spirit_breaker:1202026755595194398>"
    gyrocopter = "<:gyrocopter:1202026758132465744>"
    alchemist = "<:alchemist:1202026760607109232>"
    invoker = "<:invoker:1202026763291730000>"
    silencer = "<:silencer:1202026765791547422>"
    obsidian_destroyer = "<:obsidian_destroyer:1202026767863533568>"
    lycan = "<:lycan:1202026770031706184>"
    brewmaster = "<:brewmaster:1202026772653408297>"
    shadow_demon = "<:shadow_demon:1202026775412998214>"
    lone_druid = "<:lone_druid:1202026778282168341>"
    chaos_knight = "<:chaos_knight:1202026781033644112>"
    meepo = "<:meepo:1202026783650893855>"
    treant = "<:treant:1202026786188443718>"
    ogre_magi = "<:ogre_magi:1202026788486909982>"
    undying = "<:undying:1202026790932205672>"
    # guild 3
    rubick = "<:rubick:1202027073464717373>"
    disruptor = "<:disruptor:1202027076316565575>"
    nyx_assassin = "<:nyx_assassin:1202027079475150898>"
    naga_siren = "<:naga_siren:1202027082058838117>"
    keeper_of_the_light = "<:keeper_of_the_light:1202029134101106718>"
    wisp = "<:wisp:1202029137280114760>"
    visage = "<:visage:1202029140811984918>"
    slark = "<:slark:1202029143190155304>"
    medusa = "<:medusa:1202029145563861012>"
    troll_warlord = "<:troll_warlord:1202029147937833000>"
    centaur = "<:centaur:1202029150282719283>"
    magnataur = "<:magnataur:1202029152694440029>"
    shredder = "<:shredder:1202029155366215752>"
    bristleback = "<:bristleback:1202029157710823464>"
    tusk = "<:tusk:1202029160072220692>"
    skywrath_mage = "<:skywrath_mage:1202029162408464404>"
    abaddon = "<:abaddon:1202029164312674396>"
    elder_titan = "<:elder_titan:1202029166044917791>"
    legion_commander = "<:legion_commander:1202029169152892928>"
    techies = "<:techies:1202029171480731682>"
    ember_spirit = "<:ember_spirit:1202029174156427284>"
    earth_spirit = "<:earth_spirit:1202029176711041035>"
    abyssal_underlord = "<:abyssal_underlord:1202029179567358022>"
    terrorblade = "<:terrorblade:1202029182381723740>"
    phoenix = "<:phoenix:1202029184621219920>"
    oracle = "<:oracle:1202029187024556042>"
    winter_wyvern = "<:winter_wyvern:1202029189595922492>"
    arc_warden = "<:arc_warden:1202029192255119402>"
    monkey_king = "<:monkey_king:1202029194666582087>"
    dark_willow = "<:dark_willow:1202029197061787718>"
    pangolier = "<:pangolier:1202029199636824125>"
    grimstroke = "<:grimstroke:1202029202031779841>"
    hoodwink = "<:hoodwink:1202029204506693685>"
    void_spirit = "<:void_spirit:1202029206469623841>"
    snapfire = "<:snapfire:1202029208574890017>"
    mars = "<:mars:1202029210567446558>"
    dawnbreaker = "<:dawnbreaker:1202029213549592586>"
    marci = "<:marci:1202029215982293003>"
    primal_beast = "<:primal_beast:1202029218167529502>"
    muerta = "<:muerta:1202029220616994926>"
