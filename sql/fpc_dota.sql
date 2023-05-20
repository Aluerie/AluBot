CREATE TABLE IF NOT EXISTS dota_settings (
    guild_id BIGINT PRIMARY KEY,
    guild_name TEXT,
    channel_id BIGINT,
    spoil BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS dota_players (
    name_lower TEXT PRIMARY KEY NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    twitch_id BIGINT
);

CREATE TABLE IF NOT EXISTS dota_favourite_players (
    guild_id BIGINT PRIMARY KEY,
    player_name TEXT NOT NULL,

    CONSTRAINT fk_guild_id
        FOREIGN KEY (guild_id)
        REFERENCES dota_settings(guild_id) ON DELETE CASCADE,
    CONSTRAINT fk_player
        FOREIGN KEY (player_name)
        REFERENCES dota_players(name_lower) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dota_favourite_characters (
    guild_id BIGINT PRIMARY KEY,
    character_id INT NOT NULL,

    CONSTRAINT fk_guild_id
        FOREIGN KEY (guild_id)
        REFERENCES dota_settings(guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dota_accounts (
    id BIGINT PRIMARY KEY,
    friend_id BIGINT,
    name_lower TEXT NOT NULL,
    CONSTRAINT fk_player
        FOREIGN KEY (name_lower)
        REFERENCES dota_players(name_lower) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dota_matches (
    match_id BIGINT PRIMARY KEY,
    is_finished BOOLEAN DEFAULT FALSE,
    opendota_jobid BIGINT
);

CREATE TABLE IF NOT EXISTS dota_messages (
    message_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    match_id BIGINT NOT NULL,
    character_id INTEGER NOT NULL,
    twitch_status TEXT NOT NULL,

    CONSTRAINT fk_match
        FOREIGN KEY (match_id)
            REFERENCES dota_matches(match_id) ON DELETE CASCADE
);