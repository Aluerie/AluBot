# Some SQL recipes

I probably should make a GitHub gist instead of cluttering the bot repository, but idk. Here is a list of some quick SQL sources and recipes that I seem to always forget.

## Other Sources

* [Gist with same purpose from @SinBad](https://gist.github.com/mikeshardmind/d7d2c6cb19b53ab76b7d401b2716df5d)
  
## My Recipes

Disclaimer: maybe some of these are bad. I'm learning.

1. Recipe for converting column to tz aware

    ```sql
    ALTER TABLE bot_info ALTER COLUMN git_checked_dt
    TYPE TIMESTAMPTZ USING git_checked_dt AT TIME ZONE 'UTC';
    ```

2. Recipe to set default

    ```sql
    ALTER TABLE community_members ALTER COLUMN created_at
    SET DEFAULT (now() at time zone 'utc');
    ```

3. Recipe to INSERT and return True/None if it was success

    ```sql
    INSERT INTO community_members (id, name)
    VALUES ($1, $2)
    ON CONFLICT DO NOTHING
    RETURNING True;
    ```

    then in code `value = await self.bot.pool.fetchval(query, 333356, 'hi')`

4. Recipe to add a new column

    ```sql
    ALTER TABLE dota_matches
    ADD COLUMN live BOOLEAN DEFAULT TRUE;
    ```

5. Recipe to get all column names

    ```sql
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name=$1;
    ```

6. Recipe for idk

    ```sql
    ---------
    WITH foo AS (SELECT array(SELECT dotafeed_stream_ids
    FROM guilds
    WHERE id = 759916212842659850))
    SELECT display_name
    FROM old_dota_players p
    WHERE NOT p.id=ANY(foo)
    ORDER BY similarity(display_name, 'gorgc') DESC
    LIMIT 12;
    ```

7. Recipe to backup the database.

    ```sql
    COPY (SELECT * FROM {db_name}) TO '/.alubot/{db_name}.csv' WITH CSV DELIMITER ',' HEADER
    ```
