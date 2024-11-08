CREATE TABLE IF NOT EXISTS lol_settings (
    guild_id BIGINT PRIMARY KEY,
    guild_name TEXT,
    channel_id BIGINT,
    enabled BOOLEAN DEFAULT TRUE,
    spoil BOOLEAN DEFAULT TRUE,
    twitch_live_only BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS lol_players (
    player_id SERIAL PRIMARY KEY,
    display_name TEXT NOT NULL,
    twitch_id BIGINT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS lol_favourite_players (
    guild_id BIGINT,
    player_id INT NOT NULL,

    PRIMARY KEY(guild_id, player_id),

    CONSTRAINT fk_guild_id
        FOREIGN KEY (guild_id)
        REFERENCES lol_settings(guild_id) ON DELETE CASCADE,
    CONSTRAINT fk_player_id
        FOREIGN KEY (player_id)
        REFERENCES lol_players(player_id) ON DELETE CASCADE
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
    summoner_id TEXT PRIMARY KEY,
    puuid TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL,
    game_name TEXT NOT NULL,
    tag_line TEXT NOT NULL,
    player_id INT,
    last_edited BIGINT, -- this column is needed bcs Riot API is not precise

    CONSTRAINT fk_player_id
        FOREIGN KEY (player_id)
        REFERENCES lol_players(player_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lol_messages (
    message_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    match_id BIGINT NOT NULL,
    platform TEXT NOT NULL,
    champion_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS lol_champions_info (
    id INT PRIMARY KEY,
    emote TEXT
);