## AluBot

A personal Discord bot.

---

### Description

#### Notifications about Dota/League fav live stream + fav hero/champ combination

Initial idea was to send me notifications 
when my favourite Dota 2/ League of Legends [twitch.tv](https://www.twitch.tv/) streamers pick my favourite heroes/champions.

However, the whole process grew into making the ultimate multipurpose bot 
with pretty much everything I ever needed ! 

<img src="./media/ReadMe/MainFeature.png" alt="alubot preview">

#### And so much more

Dota 2 news and League news channels with info gathered all over the internet, TextToSpeech, Confessions, 
Birthday role, Moderation, stream notificatons, timers, Welcome messages, Logging, Emote stats, 
Information, wolframalpha, Tags, Milestone members, Thanks to twitch subs, Google translate messages, Suggestions, 
Wordcloud, ToDo list, Reminders, Afk/Selfmute mode, Experience system, NSFW, Schedule for Dota 2 matches, 
Stalking my Dota 2 profile, 

Over 100 useful/fun commands.

And so much more to come.

All info in `$help` command of the bot. Join my server to use it and see features of the bot with your own eyes. 

### Follow us

* The server with the bot: [Invite link](https://discord.gg/K8FuDeP)
* The server is just a small community of [mine](https://www.twitch.tv/Aluerie)

### Reporting Bugs and Making Suggestions

* Feel free to make an issue [here](https://github.com/Aluerie/AluBot/issues/new) or write me on discord.

### Running

This bot is written under assumption of it being **only on my servers** so neither inviting it/running 
your instance of the bot will work well. And I'm honestly not a very good programmer. Nevertheless, 
1. Python `3.10` or higher is required
2. Set up venv `python3.10 -m venv venv`
3. Install dependencies `pip install -U -r requirements.txt`
4. Rename `config.example.py` into `config.py` and fill out all needed config parameters
   * notable one is you will need to PostgreSQL 9.5 or higher to fill out `POSTGRES_URL` 
5. Replace variables in `cogs/utils/var.py` with your own values
6. To configure mentioned above PostgreSQL database and create all tables you need to run `py main.py db init`
7. Run the bot with `py main.py` [^1]
   * if you want to run test version of the bot then you need to create `tlist.py` file with following template below and run the bot with an extra flag `py main.py --test` 
   
```python
"""
Just list of extensions from `./cogs` that are going to be tested with YenBot 

AluBot does not use this file at all, the bot just assumes the `test_list` empty
"""
test_list = [  # for test bot
    'embedmaker',  # just some cogs to test 
    'fun', 
    'error',  # error handler from there is handy
    'help',  # so you can look how the command looks in `$help` command
]
```
