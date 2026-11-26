# 📝 Todo

- [ ] Check that the invite link's permissions cover every AluBot feature. The list lives in `invite_link` in `src/core/bot.py` and has to match the Guild Install permissions in the Developer Portal (Installation page). Example: `guild.edit(invites_disabled=True)` failed with 403 Missing Permissions because the link doesn't request Manage Server.

## 🗑️ Drop leftover database tables

Both are kept in the daily backups, so dropping them only removes them from the live database.

- [ ] `alubot.timers_old`: the old reminders/birthdays, already moved into `alubot.scheduled_jobs` by `sql/02_scheduled_jobs.sql`.
- [ ] `alubot.auto_sync`: the test bot's autosync now keeps its state in `.temp/autosync.json`. Drop it once that change is deployed (on prod and in the home database).

```sql
DROP TABLE alubot.timers_old, alubot.auto_sync;
```
