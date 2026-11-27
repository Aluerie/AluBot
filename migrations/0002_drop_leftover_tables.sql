/* ---------------------------------------------------------------------------------------------------------------------
Drop the tables that are left over from older code (the daily backups up to 2026-11-27 still have them):

* `timers_old`: the old reminders and birthdays, moved into `scheduled_jobs` in November 2026.
* `auto_sync`: the test bot's autosync state, which now lives in `.temp/autosync.json`.

`IF EXISTS`, since a database built from the baseline never had them.
--------------------------------------------------------------------------------------------------------------------- */

DROP TABLE IF EXISTS alubot.timers_old;

DROP TABLE IF EXISTS alubot.auto_sync;
