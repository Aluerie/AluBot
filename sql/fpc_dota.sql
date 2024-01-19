CREATE TABLE IF NOT EXISTS dota_settings (
    guild_id BIGINT PRIMARY KEY,
    guild_name TEXT,
    channel_id BIGINT,
    enabled BOOLEAN DEFAULT TRUE,
    spoil BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS dota_players (
    player_id SERIAL PRIMARY KEY,
    display_name TEXT NOT NULL UNIQUE,
    twitch_id BIGINT
);

CREATE TABLE IF NOT EXISTS dota_favourite_players (
    guild_id BIGINT,
    player_id INT,

    PRIMARY KEY(guild_id, player_id),

    CONSTRAINT fk_guild_id
        FOREIGN KEY (guild_id)
        REFERENCES dota_settings(guild_id) ON DELETE CASCADE,
    CONSTRAINT fk_player_id
        FOREIGN KEY (player_id)
        REFERENCES dota_players(player_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dota_favourite_characters (
    guild_id BIGINT,
    character_id INT NOT NULL,

    PRIMARY KEY(guild_id, character_id),

    CONSTRAINT fk_guild_id
        FOREIGN KEY (guild_id)
        REFERENCES dota_settings(guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dota_accounts (
    steam_id BIGINT PRIMARY KEY,
    friend_id BIGINT,
    player_id INT,

    CONSTRAINT fk_player_id
        FOREIGN KEY (player_id)
        REFERENCES dota_players(player_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dota_messages (
    message_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    match_id BIGINT NOT NULL,
    friend_id INTEGER NOT NULL
);