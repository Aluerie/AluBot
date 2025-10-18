CREATE TABLE
    IF NOT EXISTS webhooks (
        id BIGINT PRIMARY KEY,
        channel_id BIGINT,
        guild_id BIGINT,
        url TEXT
    );

CREATE TABLE
    IF NOT EXISTS alubot_ttv_tokens (
        user_id TEXT PRIMARY KEY,
        token TEXT NOT NULL,
        refresh TEXT NOT NULL
    );