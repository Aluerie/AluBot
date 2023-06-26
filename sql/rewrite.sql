CREATE TABLE IF NOT EXISTS botvars (
    id BOOLEAN NOT NULL PRIMARY KEY DEFAULT TRUE,
    last_dota_rss_link TEXT,
    CONSTRAINT only_one_row CHECK (id)
);