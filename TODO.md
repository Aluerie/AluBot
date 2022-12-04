# TODO LIST
   ## 0.0 Keep in mind those things
1. `map` usages

   ## 1.0 Current Urgency
2. Database works
   * transfer code from `SqlAlchemy` to `asyncpg` *properly*
3. Reduce OpenDota API requests 
   * make bot.opendota_count and count amount of calls (??? maybe not or is it even possible) 
   * ctrl f all opendota calls and reduce it
4. splitlines error for patches
5. make muted by who into logs (info obtained from audit logs)
6. rewrite daily reminders into something more sophisticated 
    * put texts into database
    * generalize code creation - probably ask in discordpy (I mean 6 task creators are same code)
    * (database loop.create_task which searches for the next closets timer)
7. steam links in dota player list
8. League patches find the pic that is patch summary
9. count command usage
10. make blocked words league to be a command that takes/writes rules into database

   ## 2.0 Later 
11. make /birthday set into view modals (? check that bot in cookies )
12. autocomplete for rules and combine those two databases, please
13. Remove Warnings / maybe mutes code
    * Warn command into logs channel rather than database
14. skip beta for help command or just limit view to 25:
15. add NathanKell to reddit snipe
16. research about how to do our dota thing (is there anything better than top100 games + public profiles)
17. probably put resp.json() from aiohhtp into bot methods
18. embed builder
    * editor 
    * context menu usage 
    * find other embed makers
19. Database works
    * Code to reset/fill the database from the scratch where it's applicable (ie. `emotes`, `users`, `botinfo`)
    * Code to fill in gaps into the database where something could happened while bot was offline like check if the bot is in all guilds for `guilds` db or that users didn't join the server, skipping database addition 
    * Code to download/backup the database with the bot command or with `click.command`
    * delete unnecessary tables we made (dfmatches_asa, xxx_guilds)
    * remove milestone_achieved column
    * timestamp with time zone for time-aware > tags.created and others
20. autocomplete for tags

    ## 3.0 When we switch back to Oracle VPS
21. automatic github pull, push, requirements
     * https://github.blog/2022-02-02-build-ci-cd-pipeline-github-actions-four-steps
22. don't forget to change starting command for service tcl at vps - copy those files too
23. let's turn MandaraBot on as well and leave some tcl tutorial for future self in your discord channel

   # 4.0 NOT URGENT
24. make docstring comments to dotafeed lolfeed and config py like since it most important cogs
25. add some difference between league and dota database add logs, icon I guess
26. edge cases when people delete channels/guilds for dota/league thing
27. include context menu commands into help menu somehow IDK
28. Discord py speedups

   ## 5.0 LAST BOX
29. Solve twitter somehow IDK fok ; Task for reload twitter I think 
30. reaction roles with new selects I guess
31. Depreceated cogs = 'tags' or something
32. create better testing tech - something like variable self.test = yes (???)
33. ?tag emoji escapes 
34. ?tag pkgutil
35. abandon not scored games for match history
36. rewrite purge into something better
37. routing thing for league (some lists exist natively in Pyot)
38. look at every cog in robo danny/pycord manager/stella
39. clips twitch check 
40. custom server name for dotafeed feature
41. add league twitch name account check to league after we rewrite it a bit better (like we have in dota; current check is for lol names)
42. request_matchmaking_stats()
43. add image name for convert thing (check resolution too 112)

    ## 6.0 Future
44. add "all" key into heroes so all heroes can be traced
45. transfer emotes used in bot to 3rd server (todo while in q tier task)
46. research 'setup.py' nor 'pyproject.toml'
47. monka omega register on AWS if opendota fails again.

    ## 7.0 IMPROVE
48. remove `regex` library in favour of `re`
49. remember `a[start:stop:step]` so `a[::-1]` is reverse
50. ?tag learn async
51. learn collection lib; do research in discord abc
52. ?tag eval
53. make a few server with emotes for more interesting #emotespam or maybe even code feature where bot make some guilds and populates them with emotes
54. research TypeVar stuff
55. remember if we ever have embed limit problems we can shorten emotes into `<:_:id> instead of <:name:id>` (need to check if it works)

    ## 8.0 Impossible Future
56. unsovled mystery [0] * 30

    ## 9.0 new ideas
57. rewrite check birthdays into similar thing as timers where it just looks for next time to congraluate instead of ticking every hour
58. rewrite borthday into embeds and also unite /birthday set and timezone commands into one 
59. maybe move rules into timers too
60. smurfs for dota/lol feed is a mess
61. https://hasura.io/learn/database/postgresql/core-concepts/6-postgresql-relationships/
62. put if condition in rows thing from the point of database view 
63. make windows dev update scan similar to league/dota patches scan :D
64. fav_id thing to make serial and the whole relation thing
65. in readme check list of features
66. maybe create a help web page ^
67. ```typescript
    this.dota2.on('ready', () => {
      console.log('connected to dota game coordinator');
    });
    this.dota2.on('unready', () => {});
    ```
68. create channel with global logs for the bot as in all guilds commands usage, I guess.
69. mess around with contributing and stuff
70. rework prefix to remove constant db queries
71. i do not like our concept for database request commands as in we are doing the same job twice
72. app_commands.Transform for issues lke reminder
73. explore twitch chat bot thing xd
74. hybrid check
75. 