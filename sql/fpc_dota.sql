CREATE TABLE
    IF NOT EXISTS dota_settings (
        guild_id BIGINT PRIMARY KEY,
        guild_name TEXT,
        channel_id BIGINT,
        enabled BOOLEAN DEFAULT TRUE,
        spoil BOOLEAN DEFAULT TRUE,
        twitch_live_only BOOLEAN DEFAULT FALSE
    );

CREATE TABLE
    IF NOT EXISTS dota_players (
        player_id SERIAL PRIMARY KEY,
        display_name TEXT NOT NULL,
        twitch_id TEXT NOT NULL UNIQUE
    );

CREATE TABLE
    IF NOT EXISTS dota_favorite_players (
        guild_id BIGINT,
        player_id INT,
        PRIMARY KEY (guild_id, player_id),
        CONSTRAINT fk_guild_id FOREIGN KEY (guild_id) REFERENCES dota_settings (guild_id) ON DELETE CASCADE,
        CONSTRAINT fk_player_id FOREIGN KEY (player_id) REFERENCES dota_players (player_id) ON DELETE CASCADE
    );

CREATE TABLE
    IF NOT EXISTS dota_favorite_characters (
        guild_id BIGINT,
        character_id INT NOT NULL,
        PRIMARY KEY (guild_id, character_id),
        CONSTRAINT fk_guild_id FOREIGN KEY (guild_id) REFERENCES dota_settings (guild_id) ON DELETE CASCADE
    );

CREATE TABLE
    IF NOT EXISTS dota_accounts (
        steam_id BIGINT PRIMARY KEY,
        friend_id BIGINT,
        player_id INT,
        CONSTRAINT fk_player_id FOREIGN KEY (player_id) REFERENCES dota_players (player_id) ON DELETE CASCADE
    );

CREATE TABLE
    IF NOT EXISTS dota_messages (
        message_id BIGINT PRIMARY KEY,
        channel_id BIGINT NOT NULL,
        match_id BIGINT NOT NULL,
        friend_id INTEGER NOT NULL,
        hero_id INT NOT NULL,
        player_name TEXT --currently only used for logs so we don't double JOIN
    );

CREATE TABLE
    IF NOT EXISTS dota_heroes_info (id INT PRIMARY KEY, emote TEXT);
