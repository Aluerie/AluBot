CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE
    auto_sync (guild_id BIGINT, payload JSONB);

-- Special Bot Variables.
-- which values are properly kept/tracked between bot restarts.
-- * these variables don't really fit any other database;
-- * they aren't connected with each other, it's just some random global variables in a sense.
CREATE TABLE
    IF NOT EXISTS bot_vars (
        id BOOLEAN NOT NULL PRIMARY KEY DEFAULT TRUE,
        community_nickname_heartbeat TIMESTAMPTZ DEFAULT (NOW () AT TIME zone 'utc'),
        lol_patch TEXT, --deprecated
        twitch_last_offline TIMESTAMPTZ DEFAULT (NOW () AT TIME zone 'utc'), -- used to track if my stream crashed
        -- only row with id=TRUE is allowed so you can use this table like this without WHERE clause
        -- var: int = await self.bot.pool.fetchval("SELECT var FROM bot_vars")
        -- await self.bot.pool.execute("UPDATE bot_vars SET twitch_last_offline = $1", now)
        CONSTRAINT only_one_row CHECK (id)
    );

CREATE TABLE
    IF NOT EXISTS timers (
        id SERIAL PRIMARY KEY,
        event TEXT,
        expires_at TIMESTAMP DEFAULT (NOW () AT TIME zone 'utc'),
        created_at TIMESTAMP DEFAULT (NOW () AT TIME zone 'utc'),
        timezone TEXT NOT NULL DEFAULT 'UTC',
        data JSONB DEFAULT ('{}'::jsonb)
    );

CREATE TABLE
    IF NOT EXISTS user_settings (
        id BIGINT PRIMARY KEY, -- The discord user ID
        timezone TEXT -- The IANA alias of the timezone
    );

CREATE TABLE
    IF NOT EXISTS emote_stats_total (
        id BIGSERIAL PRIMARY KEY,
        emote_id BIGINT,
        guild_id BIGINT,
        total INTEGER DEFAULT (0)
    );

CREATE INDEX IF NOT EXISTS emote_stats_total_guild_id_idx ON emote_stats_total (guild_id);

CREATE INDEX IF NOT EXISTS emote_stats_total_emote_id_idx ON emote_stats_total (emote_id);

CREATE UNIQUE INDEX IF NOT EXISTS emote_stats_total_uniq_idx ON emote_stats_total (guild_id, emote_id);

CREATE TABLE
    IF NOT EXISTS emote_stats_last_year (
        id BIGSERIAL PRIMARY KEY,
        emote_id BIGINT,
        guild_id BIGINT,
        author_id BIGINT,
        used TIMESTAMP
    );

CREATE INDEX IF NOT EXISTS emote_stats_last_year_emote_id_idx ON emote_stats_last_year (emote_id);

CREATE INDEX IF NOT EXISTS emote_stats_last_year_guild_id_idx ON emote_stats_last_year (guild_id);

CREATE INDEX IF NOT EXISTS emote_stats_last_year_author_id_idx ON emote_stats_last_year (author_id);

CREATE INDEX IF NOT EXISTS emote_stats_last_year_used_idx ON emote_stats_last_year (used);