"""INTENTS AND PERMISSIONS.

The bot offers quite a range of different features for Public/Community/Hideout.
Extra features for the latter require extra intents/permissions.
Maybe I should create a separate bot for each "category", but at the moment the bot is quite small server-amount wise
and doesn't grow (it's just a personal for fun project), so hopefully, this lazy approach is fine.

But if we start to get gazillion "Presence" useless events clogging the bot then
I will look into creating a helping bot for the community to unload some intents.

Or maybe, it will be another way around and I will make those community-only features to be fully public!

Conclusion
----------
Either way, this is a bit overcooking on formatting and organizing part, but let's go.

The table, unfortunately, might be outdated.
"""

from discord import Intents, Permissions

__all__ = (
    "INTENTS",
    "PERMISSIONS",
)


i = Intents()  # if you ever struggle with it - try `Intents.all()`
"""
let's make a table for what we actually need those intents.
"""
# +-------------------------------+---------------------------+---------------------------+---------------------------+
# | Intents                       | Public                    | Community                 | Hideout                   |
# +===============================+===========================+===========================+===========================+
# | Guilds                        | It is highly advisable to leave this intent enabled for your bot to function. |<|<|
i.guilds = True
# | Members                       |                           | Logging                                             |<|
i.members = True
# | Moderation                    |                           | Logging                                             |<|
i.moderation = True
# | Emojis and Stickers           |                           | Logging                                             |<|
i.emojis_and_stickers = True
# | Voice States                  |                           | Logging                                             |<|
i.voice_states = True
# | Presences                     |                           | Live Stream Role                                    |<|
i.presences = True
# | Guild Messages                |                           | Logging                                             |<|
i.guild_messages = True
# | DM Messages                   |                           | Logging                                             |<|
i.dm_messages = True
# | Message content               |                           | Message content                                     |<|
i.message_content = True
# +-------------------------------+---------------------------+---------------------------+---------------------------+
INTENTS = i


p = Permissions()  # Idk why but I want to weight all these permissions carefully so
"""
let's make a table for what we actually need those permissions.
The following permissions are taken from https://discord.com/developers/applications/
in /oauth2/general Bot Permissions section
and should match what that webpage offers.
"""
# +-------------------------------+---------------------------+---------------------------+---------------------------+
# | Permission                    | Public                    | Community                 | Hideout                   |
# +===============================+===========================+===========================+===========================+
# | General Permissions                                                                                               |
# +-------------------------------+---------------------------+---------------------------+---------------------------+
# | View Audit Log                | Emote logging                                                           | <- | <- |
p.view_audit_log = True
# | Manage Roles                  |                           | .set_permissions/color roles                    | <- |
p.manage_roles = True
# | Manage Webhooks               |                           | Mimic User Webhooks                              | <- |
p.manage_webhooks = True
# | Read Messages/View Channels | Many-many .set channel functions such as FPC Notifications                | <- | <- |
p.read_messages = True
# +-------------------------------+---------------------------+---------------------------+---------------------------+
# | Text Permissions                                                                                                  |
# +-------------------------------+---------------------------+---------------------------+---------------------------+
# | Send Messages                 | Practically everywhere (i.e. FPC Notifications)                         | <- | <- |
p.send_messages = True
# | Send Messages in Threads      | Just so text commands responses can be in threads too                   | <- | <- |
p.send_messages_in_threads = True
# | Manage Messages               | /echo /purge commands, mimic user                                       | <- | <- |
p.manage_messages = True
# | Embed Links                   | Practically everywhere (i.e. FPC Notifications)                         | <- | <- |
p.embed_links = True
# | Attach Files                  | Practically everywhere (i.e. FPC Notifications)                         | <- | <- |
p.attach_files = True
# | Read Message History          | Practically everywhere (for ctx.reply)                                  | <- | <- |
p.read_message_history = True
# | Use External Emojis           | Practically everywhere to use emojis from const.Emotes                  | <- | <- |
p.external_emojis = True
# | Add Reactions                 | ?!:thinking: reactions on @AluBot mentions                              | <- | <- |
p.add_reactions = True
# +-------------------------------+---------------------------+---------------------------+---------------------------+
# | Voice Permissions                                                                                                 |
# +-------------------------------+---------------------------+---------------------------+---------------------------+
# | Connect                       | TextToSpeech commands                                                   | <- | <- |
p.connect = True
# | Speak                         | TextToSpeech commands                                                   | <- | <- |
p.speak = True
# +-------------------------------+---------------------------+---------------------------+---------------------------+
PERMISSIONS = p
