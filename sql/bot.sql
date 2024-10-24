CREATE TABLE IF NOT EXISTS webhooks (
    id BIGINT PRIMARY KEY,
    channel_id BIGINT,
    guild_id BIGINT,
    url TEXT
);
