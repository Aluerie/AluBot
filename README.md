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
4. Rename `env.env.example` to `env.env` and fill out all needed config parameters and setup your PostgreSQL
5. Replace variables in `./utils/var.py` with your own values
6. Run the bot with `py main.py -n NAME` where NAME is `alu` for AluBot or `yen` for YenBot, test version of former
7. if it is Yennifer then change `test_list` in `./utils/mybot.py` to include cogs you want to test
