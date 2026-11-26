/* ---------------------------------------------------------------------------------------------------------------------
Baseline: the `alubot` schema as it was on prod on 2026-11-26.

`scheduled_jobs` (reminders, birthdays, etc.) isn't here: `shared.scheduler` creates it on start.
--------------------------------------------------------------------------------------------------------------------- */

CREATE SCHEMA alubot;

/* --- Users -------------------------------------------------------------------------------------------------------- */

CREATE TABLE alubot.user_settings (
    id BIGINT PRIMARY KEY, -- Discord user ID
    timezone TEXT -- IANA timezone key
);

/* --- Community ---------------------------------------------------------------------------------------------------- */

CREATE TABLE alubot.community_members (
    id BIGINT PRIMARY KEY,
    name TEXT,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    experience INTEGER DEFAULT 0,
    message_count BIGINT DEFAULT 0
);

CREATE TABLE alubot.emote_stats_total (
    id BIGSERIAL PRIMARY KEY,
    emote_id BIGINT,
    guild_id BIGINT,
    total INTEGER DEFAULT 0
);

CREATE INDEX emote_stats_total_guild_id_idx ON alubot.emote_stats_total (guild_id);

CREATE INDEX emote_stats_total_emote_id_idx ON alubot.emote_stats_total (emote_id);

CREATE UNIQUE INDEX emote_stats_total_uniq_idx ON alubot.emote_stats_total (guild_id, emote_id);

CREATE TABLE alubot.emote_usage_logger (
    id BIGSERIAL PRIMARY KEY,
    emote_id BIGINT,
    guild_id BIGINT,
    author_id BIGINT,
    used TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX emote_usage_logger_emote_id_idx ON alubot.emote_usage_logger (emote_id);

CREATE INDEX emote_usage_logger_guild_id_idx ON alubot.emote_usage_logger (guild_id);

CREATE INDEX emote_usage_logger_author_id_idx ON alubot.emote_usage_logger (author_id);

CREATE INDEX emote_usage_logger_used_idx ON alubot.emote_usage_logger (used);

/* --- Bot internals ------------------------------------------------------------------------------------------------ */

CREATE TABLE alubot.bot_variables (
    /* Single row */
    id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
    dota2bugtracker_last_checked TIMESTAMPTZ DEFAULT NOW(),
    dota2bugtracker_devs TEXT[] NOT NULL DEFAULT '{}'
);

INSERT INTO alubot.bot_variables DEFAULT VALUES;
