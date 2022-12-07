-- Initial SQL tables

CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name TEXT,
    owner_id BIGINT,
    content TEXT,
    uses INTEGER DEFAULT (0),
    created_at TIMESTAMP DEFAULT (now() at time zone 'utc')
);

CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    name TEXT,
    lastseen TIMESTAMPTZ DEFAULT (now() at time zone 'utc'),
    inlvl INTEGER DEFAULT (1),
    exp INTEGER DEFAULT (0),
    cur INTEGER DEFAULT (0),
    rep INTEGER DEFAULT (0),
    tzone FLOAT DEFAULT (0.0),
    bdate TIMESTAMP,
    msg_count BIGINT,
    can_make_tags BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS emotes (
    id BIGINT PRIMARY KEY,
    name TEXT,
    animated BOOLEAN,
    month_array INTEGER ARRAY[30] DEFAULT '{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}'
);

CREATE TABLE IF NOT EXISTS botinfo (
    id BIGINT PRIMARY KEY,
    milestone_achieved INTEGER DEFAULT (0),
    suggestion_num INTEGER DEFAULT (126),
    curr_timer INTEGER DEFAULT (0),
    curr_important_timer INTEGER DEFAULT (0),
    curr_fact_timer INTEGER DEFAULT (0),
    curr_gif_timer INTEGER DEFAULT (0),
    curr_rule_timer INTEGER DEFAULT (0),
    git_checked_dt TIMESTAMPTZ DEFAULT (now() at time zone 'utc'),
    trusted_ids BIGINT ARRAY,
    irene_is_live INTEGER DEFAULT (0),
    lol_patch TEXT,
    dota_patch TEXT
);

CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT PRIMARY KEY,
    name TEXT,
    prefix TEXT,
    emote_logs_id BIGINT,
    dotafeed_ch_id BIGINT,
    dotafeed_hero_ids INTEGER ARRAY,
    dotafeed_stream_ids INTEGER ARRAY,
    dotafeed_spoils_on BOOLEAN DEFAULT TRUE,
    lolfeed_ch_id BIGINT,
    lolfeed_champ_ids INTEGER ARRAY,
    lolfeed_stream_ids INTEGER ARRAY,
    lolfeed_spoils_on BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS lolaccs (
    id TEXT PRIMARY KEY,
    name TEXT,
    platform TEXT,
    accname TEXT,
    twtv_id BIGINT,
    last_edited TEXT, -- this column is needed bcs Riot API is not precise
    fav_id INTEGER
);

CREATE TABLE IF NOT EXISTS dota_players (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    twitch_id BIGINT
);

CREATE TABLE IF NOT EXISTS dota_accounts (
    steam_id BIGINT PRIMARY KEY,
    friend_id BIGINT,
    player_id INT NOT NULL,
    CONSTRAINT fk_player
        FOREIGN KEY (player_id)
        REFERENCES dota_players(id)
            ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dota_matches (
    id BIGINT PRIMARY KEY,
    is_finished BOOLEAN DEFAULT FALSE,
    opendota_jobid BIGINT,
    fail_counter INTEGER
);

CREATE TABLE IF NOT EXISTS dota_messages (
    message_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    match_id BIGINT NOT NULL,
    hero_id INTEGER NOT NULL,
    twitch_status TEXT NOT NULL,

    CONSTRAINT fk_match FOREIGN KEY (match_id) REFERENCES dota_matches(id)
);



CREATE TABLE IF NOT EXISTS reminders (
    id SERIAL PRIMARY KEY,
    name TEXT,
    userid BIGINT,
    channelid BIGINT,
    dtime TIMESTAMP
);

CREATE TABLE IF NOT EXISTS todonotes (
    id SERIAL PRIMARY KEY,
    name TEXT,
    userid BIGINT
);

CREATE TABLE IF NOT EXISTS afknotes (
    id INTEGER PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS warnings (
    id SERIAL PRIMARY KEY,
    key TEXT,
    name TEXT,
    dtime TIMESTAMP,
    userid BIGINT,
    modid BIGINT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS mutes (
    id SERIAL PRIMARY KEY,
    userid BIGINT,
    dtime TIMESTAMP,
    channelid BIGINT,
    reason TEXT DEFAULT ('No reason provided')
);

CREATE TABLE IF NOT EXISTS serverrules (
    id SERIAL PRIMARY KEY,
    text TEXT
);

CREATE TABLE IF NOT EXISTS realrules (
    id SERIAL PRIMARY KEY,
    text TEXT
);

CREATE TABLE IF NOT EXISTS dfmatches (
    id BIGINT PRIMARY KEY,
    match_id BIGINT,
    ch_id BIGINT,
    hero_id INTEGER,
    twitch_status TEXT,
    live BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS lfmatches (
    id BIGINT PRIMARY KEY,
    match_id TEXT,
    ch_id BIGINT,
    champ_id INTEGER,
    routing_region TEXT
);

CREATE TABLE IF NOT EXISTS dotahistory (
    id BIGINT PRIMARY KEY,
    hero_id INTEGER,
    winloss BOOLEAN,
    mmr INTEGER,
    role INTEGER,
    dtime TIMESTAMP,
    patch TEXT,
    patch_letter TEXT,
    custom_note TEXT
);