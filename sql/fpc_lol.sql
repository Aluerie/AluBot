CREATE TABLE IF NOT EXISTS lol_settings (
    guild_id BIGINT PRIMARY KEY,
    guild_name TEXT,
    channel_id BIGINT,
    spoil BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS lol_players (
    name_lower TEXT PRIMARY KEY NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    twitch_id BIGINT
);

CREATE TABLE IF NOT EXISTS lol_favourite_players (
    guild_id BIGINT,
    player_name TEXT NOT NULL,

    PRIMARY KEY(guild_id, player_name),

    CONSTRAINT fk_guild_id
        FOREIGN KEY (guild_id)
        REFERENCES lol_settings(guild_id) ON DELETE CASCADE,
    CONSTRAINT fk_player
        FOREIGN KEY (player_name)
        REFERENCES lol_players(name_lower) ON DELETE CASCADE
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
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    account TEXT NOT NULL,
    name_lower TEXT NOT NULL,
    last_edited BIGINT, -- this column is needed bcs Riot API is not precise
    CONSTRAINT fk_player
        FOREIGN KEY (name_lower)
        REFERENCES lol_players(name_lower) ON DELETE CASCADE
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