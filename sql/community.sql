CREATE TABLE IF NOT EXISTS real_rules (
    id SERIAL PRIMARY KEY,
    content VARCHAR(2000) NOT NULL
);

CREATE TABLE IF NOT EXISTS community_members (
    id BIGINT PRIMARY KEY,
    name TEXT,
    last_seen TIMESTAMPTZ DEFAULT (now() at time zone 'utc'),
    exp INTEGER DEFAULT (0),
    rep INTEGER DEFAULT (0),
    msg_count BIGINT DEFAULT (0),
    in_lvl BOOLEAN DEFAULT TRUE,
    roles BIGINT ARRAY
);
