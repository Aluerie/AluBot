# TODO LIST
   ## 0.0 Keep in mind those things
1. `map` usages

   ## 1.0 Current Urgency
2. Database works - transfer the database to `asyncpg`
3. Reduce OpenDota API requests 
   * make bot.opendota_count and count amount of calls (??? maybe not or is it even possible) 
   * ctrl f all opendota calls and reduce it
4. splitlines error for patches
5. make muted by who into logs (info obtained from audit logs)
6. rewrite daily reminders into something more sophisticated 
    * put texts into database
    * generalize code creation - probably ask in discordpy (I mean 6 task creators are same code)
    * (database loop.create_task which searches for the next closets timer)
7. League patches find the pic that is patch summary
8. count command usage
9. make blocked words league to be a command that takes/writes rules into database

   ## 2.0 Later 
10. make /birthday set into view modals (? check that bot in cookies )
11. autocomplete for rules and combine rules and timers databases
12. Remove Warnings / maybe mutes code
    * Warn command into logs channel rather than database
13. skip beta for help command or just limit view to 25:
14. add NathanKell to reddit snipe
15. research about how to do our dota thing (is there anything better than top100 games + public profiles)
16. embed builder
    * editor 
    * context menu usage 
    * find other embed makers
17. Database works
    * Code to reset/fill the database from the scratch where it's applicable (ie. `emotes`, `users`, `botinfo`)
    * Code to fill in gaps into the database where something could happened while bot was offline like check if the bot is in all guilds for `guilds` db or that users didn't join the server, skipping database addition 
    * Code to download/backup the database with the bot command or with `click.command`
    * delete unnecessary tables we made (dfmatches_asa, xxx_guilds)
    * remove milestone_achieved column
    * timestamp with time zone for time-aware > tags.created and others
18. autocomplete for tags

    ## 3.0 When we switch back to Oracle VPS
19. automatic github pull, push, requirements
     * https://github.blog/2022-02-02-build-ci-cd-pipeline-github-actions-four-steps
20. don't forget to change starting command for service tcl at vps - copy those files too
21. let's turn MandaraBot on as well and leave some tcl tutorial for future self in your discord channel

   # 4.0 NOT URGENT
22. add some difference between league and dota database add logs, icon I guess
23. edge cases when people delete channels/guilds for dota/league thing
24. include context menu commands into help menu somehow IDK
25. Discord py speedups

   ## 5.0 LAST BOX
26. Solve twitter somehow IDK fok ; Task for reload twitter I think 
27. reaction roles with new selects I guess
28. Depreceated cogs = 'tags' or something
29. ?tag emoji escapes 
30. ?tag pkgutil
31. abandon not scored games for match history
32. rewrite purge into something better
33. routing thing for league (some lists exist natively in Pyot)
34. look at every cog in robo danny/pycord manager/stella
35. clips twitch check 
36. custom server name for dotafeed feature
37. add league twitch name account check to league after we rewrite it a bit better (like we have in dota; current check is for lol names)
38. request_matchmaking_stats()
39. add image name for convert thing (check resolution too 112)

    ## 6.0 Future
40. add "all" key into heroes so all heroes can be traced
41. transfer emotes used in bot to 3rd server (todo while in q tier task)
42. research 'setup.py' nor 'pyproject.toml'
43. monka omega register on AWS if opendota fails again.

    ## 7.0 IMPROVE
44. remove `regex` library in favour of `re`
45. remember `a[start:stop:step]` so `a[::-1]` is reverse
46. ?tag learn async
47. learn collection lib; do research in discord abc
48. ?tag eval
49. make a few server with emotes for more interesting #emotespam or maybe even code feature where bot make some guilds and populates them with emotes
50. research TypeVar stuff
51. remember if we ever have embed limit problems we can shorten emotes into `<:_:id> instead of <:name:id>` (need to check if it works)

    ## 8.0 Impossible Future
52. unsolved mystery [0] * 30

    ## 9.0 new ideas
53. rewrite check birthdays into similar thing as timers where it just looks for next time to congraluate instead of ticking every hour
54. rewrite birthday into embeds and also unite /birthday set and timezone commands into one 
55. maybe move rules into timers too
56. make windows dev update scan similar to league/dota patches scan :D
57. in readme check list of features
58. maybe create a help web page ^
59. ```typescript
    this.dota2.on('ready', () => {
      console.log('connected to dota game coordinator');
    });
    this.dota2.on('unready', () => {});
    ```
60. create channel with global logs for the bot as in all guilds commands usage, I guess.
61. mess around with contributing and stuff
62. rework prefix to remove constant db queries
63. i do not like our concept for database request commands as in we are doing the same job twice
64. app_commands.Transform for issues lke reminder
65. explore twitch chat bot thing xd
66. hybrid check
67. ?tag autocomplete transformer
68. think of proper testing without this two accounts/tokens deal
69. proper duplicates removal `list(dict.fromkeys(precise_match + close_match))`
70. logic issue with those streamers who manually post vods - it takes their prelast vod as in [-1]. 
    we probably need to check time of the video as well.
71. fix cmlist error when logging into steam
72. 