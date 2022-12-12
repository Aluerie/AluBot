# TODO LIST
   ## 0.0 Keep in mind those things
1. `map` usages
2. add amount of games into opendota rate_limit

   ## 1.0 Current Urgency
3. Database works - transfer the database to `asyncpg`
4. Reduce OpenDota API requests 
   * try to involve cache into giving the limit too
   * ctrl f all opendota calls and reduce it
5. splitlines error for patches
6. make muted by who into logs (info obtained from audit logs)
7. rewrite daily reminders into something more sophisticated 
    * put texts into database
    * generalize code creation - probably ask in discordpy (I mean 6 task creators are same code)
    * (database loop.create_task which searches for the next closets timer)
8. League patches find the pic that is patch summary
9. count command usage
10. make blocked words league to be a command that takes/writes rules into database

    ## 2.0 Later 
11. make /birthday set into view modals (? check that bot in cookies )
12. autocomplete for rules and combine rules and timers databases
13. Remove Warnings / maybe mutes code
    * Warn command into logs channel rather than database
14. skip beta for help command or just limit view to 25:
15. add NathanKell to reddit snipe
16. research about how to do our dota thing (is there anything better than top100 games + public profiles)
17. embed builder
    * editor 
    * context menu usage 
    * find other embed makers
18. Database works
    * Code to reset/fill the database from the scratch where it's applicable (ie. `emotes`, `users`, `botinfo`)
    * Code to fill in gaps into the database where something could happened while bot was offline like check if the bot is in all guilds for `guilds` db or that users didn't join the server, skipping database addition 
    * Code to download/backup the database with the bot command or with `click.command`
    * delete unnecessary tables we made (dfmatches_asa, xxx_guilds)
    * remove milestone_achieved column
    * timestamp with time zone for time-aware > tags.created and others
19. autocomplete for tags

    ## 3.0 When we switch back to Oracle VPS
20. automatic github pull, push, requirements
     * https://github.blog/2022-02-02-build-ci-cd-pipeline-github-actions-four-steps
21. don't forget to change starting command for service tcl at vps - copy those files too
22. let's turn MandaraBot on as well and leave some tcl tutorial for future self in your discord channel

   # 4.0 NOT URGENT
23. add some difference between league and dota database add logs, icon I guess
24. edge cases when people delete channels/guilds for dota/league thing
25. include context menu commands into help menu somehow IDK
26. Discord py speedups

   ## 5.0 LAST BOX
27. Solve twitter somehow IDK fok ; Task for reload twitter I think 
28. reaction roles with new selects I guess
29. Depreceated cogs = 'tags' or something
30. ?tag emoji escapes 
31. ?tag pkgutil
32. abandon not scored games for match history
33. rewrite purge into something better
34. routing thing for league (some lists exist natively in Pyot)
35. look at every cog in robo danny/pycord manager/stella
36. clips twitch check 
37. custom server name for dotafeed feature
38. add league twitch name account check to league after we rewrite it a bit better (like we have in dota; current check is for lol names)
39. request_matchmaking_stats()
40. add image name for convert thing (check resolution too 112)

    ## 6.0 Future
41. add "all" key into heroes so all heroes can be traced
42. transfer emotes used in bot to 3rd server (todo while in q tier task)
43. research 'setup.py' nor 'pyproject.toml'
44. monka omega register on AWS if opendota fails again.

    ## 7.0 IMPROVE
45. remove `regex` library in favour of `re`
46. remember `a[start:stop:step]` so `a[::-1]` is reverse
47. ?tag learn async
48. learn collection lib; do research in discord abc
49. ?tag eval
50. make a few server with emotes for more interesting #emotespam or maybe even code feature where bot make some guilds and populates them with emotes
51. research TypeVar stuff
52. remember if we ever have embed limit problems we can shorten emotes into `<:_:id> instead of <:name:id>` (need to check if it works)

    ## 8.0 Impossible Future
53. unsolved mystery [0] * 30

    ## 9.0 new ideas
54. rewrite check birthdays into similar thing as timers where it just looks for next time to congraluate instead of ticking every hour
55. rewrite birthday into embeds and also unite /birthday set and timezone commands into one 
56. maybe move rules into timers too
57. make windows dev update scan similar to league/dota patches scan :D
58. in readme check list of features
59. maybe create a help web page ^
60. ```typescript
    this.dota2.on('ready', () => {
      console.log('connected to dota game coordinator');
    });
    this.dota2.on('unready', () => {});
    ```
61. create channel with global logs for the bot as in all guilds commands usage, I guess.
62. mess around with contributing and stuff
63. rework prefix to remove constant db queries
64. i do not like our concept for database request commands as in we are doing the same job twice
65. app_commands.Transform for issues lke reminder
66. explore twitch chat bot thing xd
67. hybrid check
68. ?tag autocomplete transformer
69. think of proper testing without this two accounts/tokens deal
70. proper duplicates removal `list(dict.fromkeys(precise_match + close_match))`
71. logic issue with those streamers who manually post vods - it takes their prelast vod as in [-1]. 
    we probably need to check time of the video as well.
72. fix cmlist error when logging into steam
73. 