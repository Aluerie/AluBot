/* ---------------------------------------------------------------------------------------------------------------------
Move the old `timers` into `scheduled_jobs` (`shared.scheduler`).

Run it once with psql from this folder, before or after deploying the bot that uses `shared.scheduler`:

    psql "$POSTGRES_URL" -v ON_ERROR_STOP=1 -f sql/02_scheduled_jobs.sql

* It creates `scheduled_jobs` if the bot hasn't yet.
* Reminders and birthdays keep the time on their owner's clocks (`expires_at AT TIME ZONE timezone`).
* The old table is renamed to `timers_old`, not dropped. Once everything works, drop it:
  `DROP TABLE alubot.timers_old;`
--------------------------------------------------------------------------------------------------------------------- */

SET search_path = alubot;

\ir ../src/shared/scheduler/schema.sql

BEGIN;

-- reminders: the author moves to `user_id`, the rest of the data keeps its names
INSERT INTO
    scheduled_jobs (kind, user_id, guild_id, local_due, timezone, data, created_at)
SELECT
    'reminder',
    (data ->> 'author_id')::BIGINT,
    (data ->> 'guild_id')::BIGINT,
    expires_at AT TIME ZONE timezone,
    timezone,
    JSONB_BUILD_OBJECT(
        'text', data ->> 'text',
        'channel_id', (data ->> 'channel_id')::BIGINT,
        'message_id', (data ->> 'message_id')::BIGINT,
        'mentions', '[]'::JSONB
    ),
    created_at
FROM
    timers
WHERE
    event = 'reminder';

-- birthdays: one keyed job per person, at midnight on their clocks
INSERT INTO
    scheduled_jobs (kind, key, user_id, local_due, timezone, data, created_at)
SELECT
    'birthday',
    'birthday:' || (data ->> 'user_id'),
    (data ->> 'user_id')::BIGINT,
    expires_at AT TIME ZONE timezone,
    timezone,
    JSONB_BUILD_OBJECT('year', data -> 'year', 'month', (data ->> 'month')::INT, 'day', (data ->> 'day')::INT),
    created_at
FROM
    timers
WHERE
    event = 'birthday'
ON CONFLICT (key) DO NOTHING;

-- birthday roles to take away at the end of somebody's birthday
INSERT INTO
    scheduled_jobs (kind, key, user_id, local_due, timezone, created_at)
SELECT
    'birthday_role',
    'birthday-role:' || (data ->> 'user_id'),
    (data ->> 'user_id')::BIGINT,
    expires_at AT TIME ZONE timezone,
    timezone,
    created_at
FROM
    timers
WHERE
    event = 'remove_birthday_role'
ON CONFLICT (key) DO NOTHING;

-- the periodic message: keep its old time, even if the new bot already picked a random one
INSERT INTO
    scheduled_jobs (kind, key, local_due, timezone, created_at)
SELECT
    'periodic_message',
    'periodic-message',
    expires_at AT TIME ZONE 'UTC',
    'UTC',
    created_at
FROM
    timers
WHERE
    event = 'periodic_message'
ORDER BY
    expires_at
LIMIT
    1
ON CONFLICT (key) DO UPDATE
SET
    local_due = EXCLUDED.local_due;

ALTER TABLE timers
RENAME TO timers_old;

COMMIT;
