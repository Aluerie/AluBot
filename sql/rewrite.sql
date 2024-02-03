CREATE EXTENSION IF NOT EXISTS pg_trgm;

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