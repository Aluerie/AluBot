CREATE EXTENSION IF NOT EXISTS pg_trgm;

/* ---------------------------------------------------------------------------------------------------------------------
Timers: reminders, birthdays, etc.
--------------------------------------------------------------------------------------------------------------------- */

CREATE TABLE
    IF NOT EXISTS timers (
        /* Timers */
        id SERIAL PRIMARY KEY,
        event TEXT NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        timezone TEXT NOT NULL DEFAULT 'UTC',
        data JSONB NOT NULL DEFAULT '{}'::jsonb
    );

-- the scheduler's main query: "the closest timer that expires within N days"
CREATE INDEX IF NOT EXISTS timers_expires_at_idx ON timers (expires_at);

-- `get_by_kwargs` / `fetch_by_kwargs` / `delete_by_kwargs` look timers up by event and by a subset of `data`
CREATE INDEX IF NOT EXISTS timers_event_idx ON timers (event);

CREATE INDEX IF NOT EXISTS timers_data_idx ON timers USING GIN (data jsonb_path_ops);

/* ---------------------------------------------------------------------------------------------------------------------
Users
--------------------------------------------------------------------------------------------------------------------- */

CREATE TABLE
    IF NOT EXISTS user_settings (
        id BIGINT PRIMARY KEY, -- The discord user ID
        timezone TEXT -- The IANA alias of the timezone
    );

/* ---------------------------------------------------------------------------------------------------------------------
Community
--------------------------------------------------------------------------------------------------------------------- */

CREATE TABLE
    IF NOT EXISTS community_members (
        id BIGINT PRIMARY KEY,
        name TEXT,
        last_seen TIMESTAMPTZ DEFAULT (NOW () AT TIME ZONE 'utc'),
        exp INTEGER DEFAULT (0),
        rep INTEGER DEFAULT (0),
        msg_count BIGINT DEFAULT (0),
        in_lvl BOOLEAN DEFAULT TRUE,
        roles BIGINT ARRAY
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
    IF NOT EXISTS emote_stats_logger (
        id BIGSERIAL PRIMARY KEY,
        emote_id BIGINT,
        guild_id BIGINT,
        author_id BIGINT,
        used TIMESTAMPTZ DEFAULT (NOW () AT TIME ZONE 'utc')
    );

CREATE INDEX IF NOT EXISTS emote_stats_logger_emote_id_idx ON emote_stats_logger (emote_id);

CREATE INDEX IF NOT EXISTS emote_stats_logger_guild_id_idx ON emote_stats_logger (guild_id);

CREATE INDEX IF NOT EXISTS emote_stats_logger_author_id_idx ON emote_stats_logger (author_id);

CREATE INDEX IF NOT EXISTS emote_stats_logger_used_idx ON emote_stats_logger (used);

/* ---------------------------------------------------------------------------------------------------------------------
Bot Variables and internals
--------------------------------------------------------------------------------------------------------------------- */


CREATE TABLE
    IF NOT EXISTS d_alubot_variables (
        id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
        dota2bugtracker_last_checked TIMESTAMPTZ DEFAULT NOW (),
        dota2bugtracker_devs TEXT[] NOT NULL DEFAULT '{}'
    );

CREATE TABLE
    IF NOT EXISTS auto_sync (
        payload JSONB
    );
