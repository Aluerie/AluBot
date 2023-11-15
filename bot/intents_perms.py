"""
Since I have a weird set of functions that greatly differs for Public/Community/Hideout usage
and thus they also differ in intents/permissions they require.

Let's weight those intents/permissions to give ourselves a reasoning why this or that should be `True`.
Maybe I should create separate bots for each
At the same time it's quite possible I will make features that are currently community-only to be public
This is why I probably should be greedy with intents/permissions
After all we are growing into multipurpose bot that can do everything.
"""
from discord import Intents, Permissions

__all__ = (
    'intents',
    'permissions',
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
intents = i


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
# | Manage Roles                  |                           | .set_permissions/colour roles                    | <- |
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
permissions = p
