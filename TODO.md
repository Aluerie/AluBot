   ## WORK ON IT RIGHT NOW.
1. Remove Warnings / maybe mutes code
   
   ## KEEP IN MIND.
2. `map` usages
3. reduce amount of files

   ## CURRENT URGENCY
0. `asyncpg` tech
   * have async sql alchemy as back up
   * https://github.com/Rapptz/RoboDanny
   * https://github.com/InterStella0/stella_bot
   * https://paste.sr.ht/~vex/e07c6b284e7423d0ee17f3c899e3fde422cec539
   * https://magicstack.github.io/asyncpg/current/
   * https://gist.github.com/jegfish/cfc7b22e72426f5ced6f87caa6920fd6
2. transfer database from Heroku to Oracle
   * write code to reset/fill the database from the scratch where it's applicable
   * write code to download/backup the database with the bot command
   * read how it should be actually done.  - maybe subclass database classes ?
   * async sqlalchemy
   * https://ahmed-nafies.medium.com/sqlalchemy-async-orm-is-finally-here-d560dfaa335d
   * https://github.com/nf1s/sqlalchemy_async_orm
   * https://codereview.stackexchange.com/questions/261362/discord-bot-using-sqlalchemy
   * https://discord.com/channels/336642139381301249/381965515721146390/976095655166631987
2. Reduce OpenDota API requests 
   * make bot.opendota_count and count amount of calls (??? maybe not) 
   * ctrl f all opendota calls and reduce it
   * divide dotafeed.py main cog into separate cogs so when opendota fails - we dont.
3. automatic github pull, push, requirements
4. GitHub thing issues into fewer posts
5. splitlines error for patches
6. make mandara bot alive
    * copy service file for both bots while you are at it
    * leave some tutorial for future self in your discord channel

   # SECOND IMPORTANT.
8. make muted by who into logs (info obtained from audit logs)
2. Warn command into logs channel rather than database
3. autocomplete for rules
4. steam links in dota player list
3. make /birthday set into view modals (? check that bot in cookies )
4. League patches find the pic that is patch summary
5. count command usage
6. rewrite daily reminders into something more sophisticated 
   * put texts into database
   * generalize code creation - probably ask in discordpy (I mean 6 task creators are same code)
   * (database loop.create_task which searches for the next closets timer)
25. skip beta for help command or just limit view to 25:
3. make blocked words league to be a command that takes/writes rules into dataabase
4. add NathanKell to reddit snipe
4. research about how to do our dota thing (is there anything better than top100 games + public profiles)
9. probably put resp.json() from aiohhtp into bot methods

   # NOT URGENT
20. embed builder
    * editor 
    * context menu usage 
    * find other embed makers
18. make docstring comments to dotafeed lolfeed and config py
3. add some difference between league and dota database add logs, icon I guess
4. edge cases when people delete channels/guilds for dota/league thing
11. context menu commands into help menu somehow IDK
12. Discord py speedups

   ## LAST BOX
26. `send_pages` `send_traceback` from `distools` into bot or ctx methods (complexity: confessions has `ntr.client` doing this)
2. Solve twitter somehow IDK fok ; Task for reload twitter I think 
3. reaction roles with new selects I guess
26. Depreceated cogs = 'tags' or something
29. create better testing tech - something like variable self.test = yes (???)
1. ?tag emoji escapes 
2. ?tag pkgutil
8. abandon not scored games for match history
7. rewrite purge into something better
1. routing thing for league (some lists exist natively in Pyot)
6. look at every cog in robo danny/pycord manager/stella
12. clips twitch check 
1. custom server name for dotafeed feature
2. add league twitch name account check to league after we rewrite it a bit better (like we have in dota; current check is for lol names)
4. request_matchmaking_stats()
2. add image name for convert thing (check resolution too 112)
1. nsfw functions
1. My own starboard | CarlBot 
2. My own polls | Poolmaker Bot

   ## Future
2. add "all" key into heroes so all heroes can be traced
3. transfer emotes used in bot to 3rd server (todo while in q tier task)
4. research 'setup.py' nor 'pyproject.toml'
5. monka omega register on AWS if opendota fails again.

   ## IMPROVE
50. remove `regex` library in favour of `re`
3. remember `a[start:stop:step]` so `a[::-1]` is reverse
4. ?tag learn async
5. learn collection lib; do research in discord abc
6. ?tag eval
7. make a few server with emotes for more interesting #emotespam or maybe even code feature where bot make some guilds and populates them with emotes
8. research TypeVar stuff
9. remember if we ever have embed limit problems we can shorten emotes into `<:_:id> instead of <:name:id>` (need to check if it works)

   ## Impossible Future 
1. Wait for async support at oracle [Git Issue](https://github.com/oracle/python-oracledb/issues/6) 
2. twitch stream live proper listener when twitch releases it
3. 