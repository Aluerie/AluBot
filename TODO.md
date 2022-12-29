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
3. Unite timezone and date in /birthday. Make list publicly available.
4. Scan insiders for Win11/Edge updates from the site

    ### Medium Priority
5. Database works
    * Code to reset/fill the database from the scratch where it's applicable (ie. `emotes`, `users`, `botinfo`)
    * Code to fill in gaps into the database where something could happened while bot was offline like check if the bot is in all guilds for `guilds` db or that users didn't join the server, skipping database addition 
    * Code to download/backup the database with the bot command or with `click.command`
    * delete unnecessary tables we made (dfmatches_asa, xxx_guilds)
    * remove milestone_achieved column
    * timestamp with time zone for time-aware > tags.created and others
6. autocomplete for tags
7. add twitch name account check into league same way as it is in dota
8. transfer emotes into 3rd server (todo in q tier task)
9. dota client maybe do something on ready/unready events
10. app_commands.Transform for issues like reminders
11. hybrid check
12. ?tag autocomplete transformer

    ### Low Priority
13. Try to involve Dota 2 cache class into using bot's session and bot's opendota limits
14. make blocked words in league news to be in the database
15. count command usage
16. skip beta for help command or just limit the view to 25:
17. add NathanKell to reddit snipe
18. add some difference between league and dota database add logs, icon I guess
19. edge cases when people delete channels/guilds for dota/league thing
20. create channel for global logs for the bot as in all guilds commands usage, I guess
21. mess around with contributing and stuff

    ### Question mark
22. Bring back opendota autoparse for people
23. explore twitch chat bot thing
24. clips twitch check
25. include context menu commands into help menu somehow idk
26. add image name for convert thing (check resolution too 112)
27. maybe create a help web page with github web pages
28. in readme check list of features

    ### Last Box
29. abandon not scored game for match history
30. reaction roles with new selects
31. clip twitch check
32. rewrite purge into something better
33. custom server name for dotafeed feature
34. solve twitter somehow idk fok - probably reload the whole extension
35. ??? cmlist when signing in into steam
36. unsolved mystery [0] x30
37. async dota 2 client but really i only need async wait_for
