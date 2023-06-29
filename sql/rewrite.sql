-- only row with id=TRUE is allowed
CREATE TABLE IF NOT EXISTS botvars (
    id BOOLEAN NOT NULL PRIMARY KEY DEFAULT TRUE,
    CONSTRAINT only_one_row CHECK (id)
);

