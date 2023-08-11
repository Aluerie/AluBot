-- only row with id=TRUE is allowed
-- so use it like this 
-- query = "SELECT var FROM botvars WHERE id=$1"
-- await self.bot.pool.fetchval(query, True)

CREATE TABLE IF NOT EXISTS botvars (
    id BOOLEAN NOT NULL PRIMARY KEY DEFAULT TRUE,

    community_nickname_heartbeat TIMESTAMPTZ DEFAULT (now() at time zone 'utc'),

    CONSTRAINT only_one_row CHECK (id)
);

CREATE TABLE auto_sync (
    guild_id BIGINT,
    payload JSONB
);

