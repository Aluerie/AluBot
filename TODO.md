# TODO LIST
   ## 0.0 Keep in mind those things
1. `map` usages
2. add amount of games into opendota rate_limit

   ## 1.0 Current Urgency
3. Database works - transfer the database to `asyncpg`
4. Reduce OpenDota API requests 
   * try to involve cache into giving the limit too
   * ctrl f all opendota calls and reduce it
5. make muted by who into logs (info obtained from audit logs)
6. rewrite daily reminders into something more sophisticated 
    * put texts into database
    * generalize code creation - probably ask in discordpy (I mean 6 task creators are same code)
    * (database loop.create_task which searches for the next closets timer)
7. count command usage
8. make blocked words league to be a command that takes/writes rules into database

   ## 2.0 Later 
9. make /birthday set into view modals (? check that bot in cookies )
10. autocomplete for rules and combine rules and timers databases
11. Remove Warnings / maybe mutes code
    * Warn command into logs channel rather than database
12. skip beta for help command or just limit view to 25:
13. add NathanKell to reddit snipe
14. research about how to do our dota thing (is there anything better than top100 games + public profiles)
15. embed builder
    * editor 
    * context menu usage 
    * find other embed makers
16. Database works
    * Code to reset/fill the database from the scratch where it's applicable (ie. `emotes`, `users`, `botinfo`)
    * Code to fill in gaps into the database where something could happened while bot was offline like check if the bot is in all guilds for `guilds` db or that users didn't join the server, skipping database addition 
    * Code to download/backup the database with the bot command or with `click.command`
    * delete unnecessary tables we made (dfmatches_asa, xxx_guilds)
    * remove milestone_achieved column
    * timestamp with time zone for time-aware > tags.created and others
17. autocomplete for tags

    ## 3.0 When we switch back to Oracle VPS
18. let's turn MandaraBot on as well and leave some tcl tutorial for future self in your discord channel

   # 4.0 NOT URGENT
19. add some difference between league and dota database add logs, icon I guess
20. edge cases when people delete channels/guilds for dota/league thing
21. include context menu commands into help menu somehow IDK
22. Discord py speedups

   ## 5.0 LAST BOX
23. Solve twitter somehow IDK fok ; Task for reload twitter I think 
24. reaction roles with new selects I guess
25. Depreceated cogs = 'tags' or something
26. ?tag emoji escapes 
27. ?tag pkgutil
28. abandon not scored games for match history
29. rewrite purge into something better
30. look at every cog in robo danny/pycord manager/stella
31. clips twitch check 
32. custom server name for dotafeed feature
33. add league twitch name account check to league after we rewrite it a bit better (like we have in dota; current check is for lol names)
34. request_matchmaking_stats()
35. add image name for convert thing (check resolution too 112)

    ## 6.0 Future
36. transfer emotes used in bot to 3rd server (todo while in q tier task)
37. research 'setup.py' nor 'pyproject.toml'
38. monka omega register on AWS if opendota fails again.

    ## 7.0 IMPROVE
39. remove `regex` library in favour of `re`
40. ?tag learn async
41. learn collection lib; do research in discord abc
42. ?tag eval
43. make a few server with emotes for more interesting #emotespam or maybe even code feature where bot make some guilds and populates them with emotes
44. research TypeVar stuff
45. remember if we ever have embed limit problems we can shorten emotes into `<:_:id> instead of <:name:id>` (need to check if it works)

    ## 8.0 Impossible Future
46. unsolved mystery [0] * 30

    ## 9.0 new ideas
47. rewrite check birthdays into similar thing as timers where it just looks for next time to congraluate instead of ticking every hour
48. rewrite birthday into embeds and also unite /birthday set and timezone commands into one 
49. maybe move rules into timers too
50. make windows dev update scan similar to league/dota patches scan :D
51. in readme check list of features
52. maybe create a help web page ^
53. ```typescript
    this.dota2.on('ready', () => {
      console.log('connected to dota game coordinator');
    });
    this.dota2.on('unready', () => {});
    ```
54. create channel with global logs for the bot as in all guilds commands usage, I guess.
55. mess around with contributing and stuff
56. rework prefix to remove constant db queries
57. i do not like our concept for database request commands as in we are doing the same job twice
58. app_commands.Transform for issues lke reminder
59. explore twitch chat bot thing xd
60. hybrid check
61. ?tag autocomplete transformer
62. think of proper testing without this two accounts/tokens deal
63. logic issue with those streamers who manually post vods - it takes their prelast vod as in [-1]. 
    we probably need to check time of the video as well.
64. fix cmlist error when logging into steam
