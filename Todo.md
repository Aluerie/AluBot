# 📝 Todo

- [ ] Check that the invite link's permissions cover every AluBot feature. The list lives in `invite_link` in `src/core/bot.py` and has to match the Guild Install permissions in the Developer Portal (Installation page). Example: `guild.edit(invites_disabled=True)` failed with 403 Missing Permissions because the link doesn't request Manage Server.
