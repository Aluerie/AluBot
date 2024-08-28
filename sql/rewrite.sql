CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE auto_sync (
    guild_id BIGINT, 
    payload JSONB
);


-- Special Bot Variables.
-- which values are properly kept/tracked between bot restarts.
-- * these variables don't really fit any other database;
-- * they aren't connected with each other, it's just some random global variables in a sense.
CREATE TABLE IF NOT EXISTS bot_vars (
    id BOOLEAN NOT NULL PRIMARY KEY DEFAULT TRUE,
    community_nickname_heartbeat TIMESTAMPTZ DEFAULT (NOW() at time zone 'utc'),
    lol_patch TEXT,
    twitch_last_offline TIMESTAMP, -- used to track if my stream crashed
    
    -- only row with id=TRUE is allowed so you can use this table like this without WHERE clause
    -- var: int = await self.bot.pool.fetchval("SELECT var FROM bot_vars")
    -- await self.bot.pool.execute("UPDATE bot_vars SET twitch_last_offline = $1", now)
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

CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    name TEXT,
    prefixes TEXT[] NOT NULL DEFAULT ARRAY['$']::TEXT[],
    premium BOOLEAN DEFAULT FALSE, -- currently unused
    emote_logs_id BIGINT, -- todo: idk i don't like it, maybe create separate guild_settings
);

-- Functions that are dispatched to a listener
-- that updates the prefix cache automatically
CREATE OR REPLACE FUNCTION update_prefixes_cache()
    RETURNS TRIGGER AS $$ 
    BEGIN 
        IF TG_OP = 'DELETE' THEN 
            PERFORM pg_notify(
                'delete_prefixes', 
                NEW.id::TEXT
            );
        ELSIF TG_OP = 'UPDATE' AND OLD.prefixes <> NEW.prefixes THEN 
            PERFORM pg_notify(
                'update_prefixes',
                JSON_BUILD_OBJECT(
                    'guild_id',
                    NEW.guild_id,
                    'prefixes',
                    NEW.prefixes
                )::TEXT
            );
        ELSIF TG_OP = 'INSERT' AND NEW.prefixes <> ARRAY []::TEXT [] THEN 
            PERFORM pg_notify(
                'update_prefixes',
                JSON_BUILD_OBJECT(
                    'guild_id',
                    NEW.guild_id,
                    'prefixes',
                    NEW.prefixes
                )::TEXT
            );
        END IF;
        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_prefixes_cache_trigger
    AFTER INSERT OR UPDATE OR DELETE 
    ON guilds 
    FOR EACH ROW 
        EXECUTE PROCEDURE update_prefixes_cache();

CREATE TABLE IF NOT EXISTS emote_stats_total (
    id BIGSERIAL PRIMARY KEY,
    emote_id BIGINT, 
    guild_id BIGINT,
    total INTEGER DEFAULT (0)
);

CREATE INDEX IF NOT EXISTS emote_stats_total_guild_id_idx ON emote_stats_total (guild_id);
CREATE INDEX IF NOT EXISTS emote_stats_total_emote_id_idx ON emote_stats_total (emote_id);
CREATE UNIQUE INDEX IF NOT EXISTS emote_stats_total_uniq_idx ON emote_stats_total (guild_id, emote_id);


CREATE TABLE IF NOT EXISTS emote_stats_last_year (
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