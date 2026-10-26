CREATE TABLE IF NOT EXISTS button_role_links (
    message_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    link_id UUID NOT NULL,
    PRIMARY KEY (message_id, role_id)
);
CREATE INDEX IF NOT EXISTS button_role_links_link_id_idx ON button_role_links (link_id);
