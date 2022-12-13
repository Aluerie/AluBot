## AluBot ❤

Initial idea was to send me notifications  when my favourite  Dota 2/ League of Legends 
[twitch.tv](https://www.twitch.tv/) streamers pick my favourite heroes/champions.

However, the whole process grew into making *the ultimate multipurpose bot*
with pretty much everything I ever needed ! Check List of features after the pic.

<img src="./media/ReadMe/MainFeature.png" alt="alubot preview">

### List of features

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
 - [X] Stalking my Dota 2 profile
 - [X] So in total Over 100 useful/fun commands.
 - [X] And so much more to come.

All info in `$help` or `/help` command of the bot. Join my server to use it and see features of the bot with your own eyes. 

### Follow us

* The server with the bot: [Invite link](https://discord.gg/K8FuDeP)
* The server is just a small community of [mine](https://www.twitch.tv/Aluerie)

### Reporting Bugs and Making Suggestions

* There are [Contributing guidelines](https://github.com/Aluerie/AluBot/blob/main/CONTRIBUTING.md)
* TL;DR^: Feel free to make an Issue/Pull Request or write me (Aluerie ❤#6524) on discord.

### Running

This bot is written under assumption of it being **only on my servers** so neither inviting it/running 
your instance of the bot will work well. And I'm honestly not a very good programmer. Nevertheless, 
1. Python `3.10` or higher is required
2. Set up venv `python3.10 -m venv venv`
3. Install dependencies `pip install -U -r requirements.txt`
4. Rename `config.example.py` into `config.py` and fill out all needed config parameters
   * notable one is you will need to PostgreSQL 9.5 or higher to fill out `POSTGRES_URL` 
5. Replace variables in `cogs/utils/var.py` with your own values
6. Create SQL tables using `sql/tables.sql` definitions with console or run `py main.py db create`
7. Run the bot with `py main.py` 
   * if you want to run test version of the bot then you need to create `tlist.py` file with 
   following template below and run the bot with an extra flag `py main.py --test` 
   
```python
"""
Just list of extensions from `./cogs` that are going to be tested with YenBot 

-- List them without `.py`-ending as in 'confessions' and not 'confessions.py'

AluBot does not use this file at all, the bot just assumes the `test_list` empty
"""
test_list = [  # for test bot
    'embedmaker',  # just some cogs to test 
    'fun', 
    'error',  # error handler from there is handy
    'help',  # so you can look how the command looks in `$help` command
]
```
### Thanks 
Thanks to everybody who has ever helped me with the bot in any way or form. 

Special thanks to the whole `discord.py` community for endless amount of educational value.
