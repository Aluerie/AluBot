CREATE TABLE IF NOT EXISTS lol_settings (
    guild_id BIGINT PRIMARY KEY,
    guild_name TEXT,
    channel_id BIGINT,
    spoil BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS lol_players (
    lower_name TEXT PRIMARY KEY NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    twitch_id BIGINT
);

CREATE TABLE IF NOT EXISTS lol_favourite_players (
    guild_id BIGINT,
    lower_name TEXT NOT NULL,

    PRIMARY KEY(guild_id, lower_name),

    CONSTRAINT fk_guild_id
        FOREIGN KEY (guild_id)
        REFERENCES lol_settings(guild_id) ON DELETE CASCADE,
    CONSTRAINT fk_player
        FOREIGN KEY (lower_name)
        REFERENCES lol_players(lower_name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lol_favourite_characters (
    guild_id BIGINT,
    character_id INT NOT NULL,

    PRIMARY KEY(guild_id, character_id),

    CONSTRAINT fk_guild_id
        FOREIGN KEY (guild_id)
        REFERENCES lol_settings(guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lol_accounts (
    id TEXT PRIMARY KEY, -- id = summoner id ; name "id" to be the same with "dota_accounts"
    platform TEXT NOT NULL,
    account_name TEXT NOT NULL,
    lower_name TEXT NOT NULL,
    last_edited BIGINT, -- this column is needed bcs Riot API is not precise
    CONSTRAINT fk_player
        FOREIGN KEY (lower_name)
        REFERENCES lol_players(lower_name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lol_matches (
    match_id BIGINT PRIMARY KEY,
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
            REFERENCES lol_matches(match_id) ON DELETE CASCADE
);