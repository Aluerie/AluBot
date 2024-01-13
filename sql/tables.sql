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
    dota_patch TEXT,
    event_pass_is_live BOOLEAN DEFAULT (FALSE),
    drop_watch_live BOOLEAN DEFAULT (FALSE)
);

CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT PRIMARY KEY,
    name TEXT,
    prefix TEXT,
    emote_logs_id BIGINT,
    birthday_channel BIGINT,
    birthday_role BIGINT
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
    probability FLOAT CHECK ( 0 < probability AND probability <= 1 ),
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

CREATE TABLE IF NOT EXISTS valve_devs (
    login TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS autoparse (
    steam_id BIGINT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS bot_vars (
    id: PRIMARY KEY BIGINT,
    last_dota_news TEXT,
    last_ms_insider_news TEXT,
    last_lol_patch TEXT,
)