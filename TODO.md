# TODO LIST
   ## 0.0 Keep in mind those things
1. `map` usages
2. reduce amount of files

   ## 1.0 Current Urgency
3. Database works
   * transfer code from `SqlAlchemy` to `asyncpg`
4. Reduce OpenDota API requests 
   * make bot.opendota_count and count amount of calls (??? maybe not or is it even possible) 
   * ctrl f all opendota calls and reduce it
   * divide dotafeed.py main cog into separate cogs so when opendota fails - we dont lose it all.
5. GitHub bugtracker issues into fewer posts
6. splitlines error for patches
7. make muted by who into logs (info obtained from audit logs)
8. rewrite daily reminders into something more sophisticated 
    * put texts into database
    * generalize code creation - probably ask in discordpy (I mean 6 task creators are same code)
    * (database loop.create_task which searches for the next closets timer)
9. steam links in dota player list
10. League patches find the pic that is patch summary
11. count command usage
12. make blocked words league to be a command that takes/writes rules into database

   ## 2.0 Later 
13. make /birthday set into view modals (? check that bot in cookies )
14. autocomplete for rules and combine those two databases, please
15. Remove Warnings / maybe mutes code
    * Warn command into logs channel rather than database
16. skip beta for help command or just limit view to 25:
17. add NathanKell to reddit snipe
18. research about how to do our dota thing (is there anything better than top100 games + public profiles)
19. probably put resp.json() from aiohhtp into bot methods
20. embed builder
    * editor 
    * context menu usage 
    * find other embed makers
21. change Intents.all() to what we actually need.
22. Database works
    * Code to reset/fill the database from the scratch where it's applicable (ie. `emotes`, `users`, `botinfo`)
    * Code to fill in gaps into the database where something could happened while bot was offline like check if the bot is in all guilds for `guilds` db or that users didn't join the server, skipping database addition 
    * Code to download/backup the database with the bot command or with `click.command`
    * delete unnecessary tables we made (dfmatches_asa, xxx_guilds)
    * remove milestone_achieved column
    * timestamp with time zone for time-aware > tags.created and others
23. autocomplete for tags

    ## 3.0 When we switch back to Oracle VPS
24. automatic github pull, push, requirements
     * https://github.blog/2022-02-02-build-ci-cd-pipeline-github-actions-four-steps
25. don't forget to change starting command for service tcl at vps - copy those files too
26. let's turn MandaraBot on as well and leave some tcl tutorial for future self in your discord channel

   # 4.0 NOT URGENT
27. make docstring comments to dotafeed lolfeed and config py like since it most important cogs
28. add some difference between league and dota database add logs, icon I guess
29. edge cases when people delete channels/guilds for dota/league thing
30. include context menu commands into help menu somehow IDK
31. Discord py speedups

   ## 5.0 LAST BOX
32. `send_pages` `send_traceback` from `distools` into bot or ctx methods (complexity: confessions has `ntr.client` doing this)
33. Solve twitter somehow IDK fok ; Task for reload twitter I think 
34. reaction roles with new selects I guess
35. Depreceated cogs = 'tags' or something
36. create better testing tech - something like variable self.test = yes (???)
37. ?tag emoji escapes 
38. ?tag pkgutil
39. abandon not scored games for match history
40. rewrite purge into something better
41. routing thing for league (some lists exist natively in Pyot)
42. look at every cog in robo danny/pycord manager/stella
43. clips twitch check 
44. custom server name for dotafeed feature
45. add league twitch name account check to league after we rewrite it a bit better (like we have in dota; current check is for lol names)
46. request_matchmaking_stats()
47. add image name for convert thing (check resolution too 112)

    ## 6.0 Future
48. add "all" key into heroes so all heroes can be traced
49. transfer emotes used in bot to 3rd server (todo while in q tier task)
50. research 'setup.py' nor 'pyproject.toml'
51. monka omega register on AWS if opendota fails again.

    ## 7.0 IMPROVE
52. remove `regex` library in favour of `re`
53. remember `a[start:stop:step]` so `a[::-1]` is reverse
54. ?tag learn async
55. learn collection lib; do research in discord abc
56. ?tag eval
57. make a few server with emotes for more interesting #emotespam or maybe even code feature where bot make some guilds and populates them with emotes
58. research TypeVar stuff
59. remember if we ever have embed limit problems we can shorten emotes into `<:_:id> instead of <:name:id>` (need to check if it works)

    ## 8.0 Impossible Future
60. unsovled mystery [0] * 30

    ## 9.0 new ideas
61. rewrite check birthdays into similar thing as timers where it just looks for next time to congraluate instead of ticking every hour
62. rewrite borthday into embeds and also unite /birthday set and timezone commands into one 
63. maybe move rules into timers too
64. smurfs for dota/lol feed is a mess
65. https://hasura.io/learn/database/postgresql/core-concepts/6-postgresql-relationships/
66. put if condition in rows thing from the point of database view 
67. make windows dev update scan similar to league/dota patches scan :D
68. fav_id thing to make serial and the whole relation thing
69. in readme check list of features
70. maybe create a help web page ^
71. ```typescript
    this.dota2.on('ready', () => {
      console.log('connected to dota game coordinator');
    });
    this.dota2.on('unready', () => {});
    ```
72. create channel with global logs for the bot as in all guilds commands usage, I guess.
73. mess around with contributing and stuff
74. move `send_pages_list(` to ctx. Problem - something is wrong when ctx is Interaction