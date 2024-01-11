CREATE TABLE auto_sync (
    guild_id BIGINT, 
    payload JSONB
);

CREATE TABLE IF NOT EXISTS botvars (
    id BOOLEAN NOT NULL PRIMARY KEY DEFAULT TRUE,
    community_nickname_heartbeat TIMESTAMPTZ DEFAULT (NOW() at time zone 'utc'),
    lol_patch TEXT,
    
    -- only row with id=TRUE is allowed
    -- so use it like this 
    -- query = "SELECT var FROM botvars WHERE id=$1"
    -- await self.bot.pool.fetchval(query, True)
    CONSTRAINT only_one_row CHECK (id)
);

CREATE TABLE IF NOT EXISTS timers (
    id SERIAL PRIMARY KEY,
    event TEXT,
    expires_at TIMESTAMP DEFAULT (NOW() at time zone 'utc'),
    created_at TIMESTAMP DEFAULT (NOW() at time zone 'utc'),
    timezone TEXT NOT NULL DEFAULT 'UTC',
    data JSONB DEFAULT ('{}'::jsonb)
);

CREATE TABLE IF NOT EXISTS user_settings (
    id BIGINT PRIMARY KEY, -- The discord user ID
    timezone TEXT -- The IANA alias of the timezone
);

CREATE TABLE IF NOT EXISTS guild_settings (
    id BIGINT,
    name TEXT,
    premium BOOLEAN DEFAULT FALSE,
)