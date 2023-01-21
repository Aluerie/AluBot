## AluBot 💜

[![Invite](
https://img.shields.io/badge/Invite%20the%20bot-link-blueviolet?style=for-the-badge&logo=discord&logoColor=7289da
)](
https://discord.com/api/oauth2/authorize?client_id=713124699663499274&scope=bot+applications.commands&permissions=2199023255551
)
![Lines of Code](
https://img.shields.io/tokei/lines/github/Aluerie/AluBot?style=for-the-badge&logo=github&color=blueviolet&label=Total%20Lines%20of%20Code
)

![Servers](
https://img.shields.io/badge/dynamic/json?style=for-the-badge&color=9678b6&logo=discord&logoColor=7289da&label=total%20servers&query=%24.servers&url=https%3A%2F%2Faluerie.github.io%2FAluBot%2Fapi%2Fdata.json
)
![Users](
https://img.shields.io/badge/dynamic/json?style=for-the-badge&color=9678b6&logo=discord&logoColor=7289da&label=total%20users&query=%24.users&url=https%3A%2F%2Faluerie.github.io%2FAluBot%2Fapi%2Fdata.json
)
![Updated](
https://img.shields.io/badge/dynamic/json?style=for-the-badge&color=9678b6&logo=none&label=<-%20Info%20updated&query=%24.updated&url=https%3A%2F%2Faluerie.github.io%2FAluBot%2Fapi%2Fdata.json)

[![Discord](
https://img.shields.io/discord/702561315478044804?style=for-the-badge&color=7289da&label=Chat%20On%20Discord&logo=discord&logoColor=7289da
)](
https://discord.gg/K8FuDeP
)
[![Dashboard](
https://img.shields.io/badge/bot's%20website-link-9400d3?style=for-the-badge&logo=githubsponsors&logoColor=9400d3
)](
https://aluerie.github.io/AluBot/
)

Initial idea was to send me notifications  when my favourite  Dota 2/ League of Legends 
[twitch.tv](https://www.twitch.tv/) streamers pick my favourite heroes/champions.

However, the whole process grew into making *the ultimate multipurpose bot*
with pretty much everything I ever needed ! Check List of features after the pic.

<img src="./media/ReadMe/MainFeature.png" alt="alubot preview">

### 📖 List of features

All info in `$help` or `/help` command of the bot. But here is list that is probably not full:
 - [X] maintains #🍋dota2_news
   * [Dota 2 Bugtracker](https://github.com/ValveSoftware/Dota2-Gameplay) updates - comments from Valve employees  
   * Steam DB's [GameTracking-Dota2](https://github.com/SteamDatabase/GameTracking-Dota2) updates and its analysis
   * Twitter, Reddit comments/posts from known accounts
 - [X] #🔬lol_news announcement channel
 - [X] TextToSpeech
 - [X] Confessions
 - [X] Birthday role and congratulations 
 - [X] Moderation
 - [X] Twitch starting stream notifications
 - [X] Timers
 - [X] Welcome messages
 - [X] Logging
 - [X] Emote stats
 - [X] Info commands
 - [X] WolframAlpha queries commands
 - [X] Tags system 
 - [X] Google translate messages
 - [X] Suggestion commands
 - [X] Wordcloud
 - [X] ToDo list
 - [X] Reminders 
 - [X] AFK/Selfmute commands
 - [X] NSFW 
 - [X] Schedule for Dota 2 matches
 - [X] Stalking my Dota 2 profile (despite my "Expose data" setting is off)
 - [X] So in total Over 100 useful/fun commands.
 - [X] And so much more to come.


### 🤝 Reporting Bugs, Making Suggestions and Contributing

* There are [Contributing guidelines](https://github.com/Aluerie/AluBot/blob/main/.github/CONTRIBUTING.md)
* TL;DR^: Feel free to...
  * open a GitHub Issue/PR/Discussion
  * Use `/feedback` bot command 
  * write me (Aluerie ❤#6524) on discord
  * look my [Project](https://github.com/users/Aluerie/projects/8/views/1) for ideas to contribute.

### 🛠️Running

I would probably prefer if you don't run an instance of my bot. You can invite the bot to your server with link above,
discord native interface or `$invite` command.
And I'm honestly not a very good programmer. Nevertheless, 
1. Python `3.10` or higher is required.
2. Set up venv `python3.10 -m venv venv`.
3. Install dependencies `pip install -U -r requirements.txt`.
4. Rename `config.example.py` into `config.py` and fill out all needed config parameters.
   * notable one is you will need to PostgreSQL 9.5 or higher to fill out `POSTGRES_URL`.
5. Replace discord ID variables in `cogs/utils/var.py` with your own values.
6. Create SQL tables using `sql/tables.sql` definitions with console or run `py main.py db create`.
7. Run the bot with `py main.py`.
   * if you want to run test version of the bot then you need to create `tlist.py` file with 
   following template below and run the bot with an extra flag `py main.py --test` 
   
```python
"""
List of extensions from `./cogs` to test. The bot will load only extensions from that list. 

-- List them without `.py`-ending as in 'confessions' and not 'confessions.py'

Actual AluBot does not use this file at all, the bot just assumes the `test_list` empty
"""
test_list = [  # for test bot
    'embedmaker',  # just some cogs to test 
    'fun', 
    'error',  # global error handlers from there are handy
    'meta',  # it has /$help, /$setup, so you can look how your new commands looks here
]
```
### 🤗Thanks 
Thanks to everybody who has ever helped me with the bot in any way or form. 

Special thanks to the whole `discord.py` community for endless amount of educational value.

### 🕵️ Privacy Policy and Terms of Service

Some personal data is stored with a consent of the user.
 
Example of such commands is `/birthday set`. 
If you are using the command - you are giving me consent to store your birthday data, 
work with it and show to other people. 

The bot have commands to delete your data, i.e. `/birthday remove`.
