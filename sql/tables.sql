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
    exp INTEGER DEFAULT (0),
    cur INTEGER DEFAULT (0),
    rep INTEGER DEFAULT (0),
    tzone TEXT,
    bdate TIMESTAMPTZ,
    msg_count BIGINT DEFAULT (0),
    can_make_tags BOOLEAN DEFAULT TRUE,
    inlvl BOOLEAN DEFAULT TRUE
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
    dota_patch TEXT,
    event_pass_is_live BOOLEAN DEFAULT (FALSE),
    drop_watch_live BOOLEAN DEFAULT (FALSE)

);

CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT PRIMARY KEY,
    name TEXT,
    prefix TEXT,
    emote_logs_id BIGINT,
    dotafeed_ch_id BIGINT,
    dotafeed_hero_ids INTEGER ARRAY DEFAULT ARRAY[]::INTEGER[],
    dotafeed_stream_ids INTEGER ARRAY DEFAULT ARRAY[]::INTEGER[],
    dotafeed_spoils_on BOOLEAN DEFAULT TRUE,
    lolfeed_ch_id BIGINT,
    lolfeed_champ_ids INTEGER ARRAY DEFAULT ARRAY[]::INTEGER[],
    lolfeed_stream_ids INTEGER ARRAY DEFAULT ARRAY[]::INTEGER[],
    lolfeed_spoils_on BOOLEAN DEFAULT TRUE,
    birthday_channel BIGINT,
    birthday_role BIGINT
);

CREATE TABLE IF NOT EXISTS dota_players (
    id SERIAL PRIMARY KEY,
    name_lower TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    twitch_id BIGINT
);

CREATE TABLE IF NOT EXISTS dota_accounts (
    id BIGINT PRIMARY KEY,
    friend_id BIGINT,
    player_id INT NOT NULL,
    CONSTRAINT fk_player
        FOREIGN KEY (player_id)
        REFERENCES dota_players(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dota_matches (
    id BIGINT PRIMARY KEY,
    is_finished BOOLEAN DEFAULT FALSE,
    opendota_jobid BIGINT
);

CREATE TABLE IF NOT EXISTS dota_messages (
    message_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    match_id BIGINT NOT NULL,
    hero_id INTEGER NOT NULL,
    twitch_status TEXT NOT NULL,

    CONSTRAINT fk_match
        FOREIGN KEY (match_id)
            REFERENCES dota_matches(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lol_players (
    id SERIAL PRIMARY KEY,
    name_lower TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    twitch_id BIGINT
);

CREATE TABLE IF NOT EXISTS lol_accounts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    account_name TEXT NOT NULL,
    player_id INT NOT NULL,
    last_edited BIGINT, -- this column is needed bcs Riot API is not precise
    CONSTRAINT fk_player
        FOREIGN KEY (player_id)
        REFERENCES lol_players(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lol_matches (
    id BIGINT PRIMARY KEY,
    platform TEXT NOT NULL,
    region TEXT NOT NULL,
    is_finished BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS lol_messages (
    message_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    match_id BIGINT NOT NULL,
    champ_id INTEGER NOT NULL,

    CONSTRAINT fk_match
        FOREIGN KEY (match_id)
            REFERENCES lol_matches(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reminders (
    id SERIAL PRIMARY KEY,
    event TEXT,
    expires TIMESTAMPTZ DEFAULT (now() at time zone 'utc'),
    created TIMESTAMPTZ DEFAULT (now() at time zone 'utc'),
    extra JSONB DEFAULT ('{}'::jsonb)
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

CREATE TABLE IF NOT EXISTS timer_categories (
    id SERIAL PRIMARY KEY,
    name TEXT,
    frequency INTERVAL,
    probability FLOAT CHECK ( 0 < probability <= 1 ),
    start_dt TIMESTAMP DEFAULT (now() at time zone 'utc'),
    channel_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS timer_texts (
    id SERIAL PRIMARY KEY,
    author_id BIGINT NOT NULL,
    category_id INTEGER,
    text TEXT,

    CONSTRAINT fk_match
        FOREIGN KEY (category_id)
            REFERENCES timer_categories(id) ON DELETE CASCADE
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