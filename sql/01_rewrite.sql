/* ---------------------------------------------------------------------------------------------------------------------
Timers 
--------------------------------------------------------------------------------------------------------------------- */

CREATE TABLE 
    IF NOT EXISTS timers (
        
        id SERIAL PRIMARY KEY,
        event TEXT NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        timezone TEXT NOT NULL DEFAULT 'UTC',
        data JSONB NOT NULL DEFAULT '{}'::jsonb
    );

CREATE INDEX IF NOT EXISTS timers_expires_at_idx ON timers (expires_at);