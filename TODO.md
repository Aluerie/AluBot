### TODO

0. Check when Valve people make their own issues as well

### High Priority
1. Rewrite daily reminders into something more sophisticated
    * put texts into database
    * generalize code creation - probably ask in discordpy (I mean 6 task creators are same code)
    * (database loop.create_task which searches for the next closets timer)
    * put rules in there with /rules /realrules commands (as in bring back rules.py)
    * autocomplete for rules and maybe for timers
2. Bring back reminders_todo.py
3. Make muted by who to go into logs (from audit logs)
4. Unite timezone and date in /birthday. Make list publicly available.
5. Scan insiders for Win11/Edge updates from the site

    ### Medium Priority
6. Embed Builder
    * editor 
    * context menu usage 
    * find other embed makers
7. Database works
    * Code to reset/fill the database from the scratch where it's applicable (ie. `emotes`, `users`, `botinfo`)
    * Code to fill in gaps into the database where something could happened while bot was offline like check if the bot is in all guilds for `guilds` db or that users didn't join the server, skipping database addition 
    * Code to download/backup the database with the bot command or with `click.command`
    * delete unnecessary tables we made (dfmatches_asa, xxx_guilds)
    * remove milestone_achieved column
    * timestamp with time zone for time-aware > tags.created and others
8. autocomplete for tags
9. add twitch name account check into league same way as it is in dota
10. transfer emotes into 3rd server (todo in q tier task)
11. dota client maybe do something on ready/unready events
12. app_commands.Transform for issues like reminders
13. hybrid check
14. ?tag autocomplete transformer

    ### Low Priority
15. Try to involve Dota 2 cache class into using bot's session and bot's opendota limits
16. make blocked words in league news to be in the database
17. count command usage
18. skip beta for help command or just limit the view to 25:
19. add NathanKell to reddit snipe
20. add some difference between league and dota database add logs, icon I guess
21. edge cases when people delete channels/guilds for dota/league thing
22. create channel for global logs for the bot as in all guilds commands usage, I guess
2*3. mess around with contributing and stuff

    ### Question mark
23. Bring back opendota autoparse for people
24. explore twitch chat bot thing
25. let's turn mandara bot on as well
26. clips twitch check
27. include context menu commands into help menu somehow idk
28. add image name for convert thing (check resolution too 112)
29. maybe create a help web page with github web pages
30. in readme check list of features

    ### Last Box
31. ?tag emoji escapes
32. abandon not scored game for match history
33. request_matchmakign_stats()
34. research `setup.py` and `pyproject.toml`
35. reaction roles with new selects
36. clip twitch chek
37. rewrite purge into something better
38. custom server name for dotafeed feature
39. solve twitter somehow idk fok - probably reload the whole extension
40. ?tag pkgutil
41. ??? cmlist when signing in into steam
42. unsolved mystery [0] x30
43. async dota 2 client but really i only need async wait_for

   ### Learn Material
44. `map` usage
45. regex vs re library ?
46. ?tag learn async
47. learn collections lib, research discord abc, research TypeVar
48. ?tag eval
49. check if trick <:name:id> versis <:_:id> works for embed limits