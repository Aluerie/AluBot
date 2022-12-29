### TODO

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
8. dota client maybe do something on ready/unready events
9. app_commands.Transform for issues like reminders
10. hybrid check
11. ?tag autocomplete transformer

    ### Low Priority
12. Try to involve Dota 2 cache class into using bot's session and bot's opendota limits
13. make blocked words in league news to be in the database
14. count command usage
15. skip beta for help command or just limit the view to 25:
16. add NathanKell to reddit snipe
17. add some difference between league and dota database add logs, icon I guess
18. edge cases when people delete channels/guilds for dota/league thing
19. create channel for global logs for the bot as in all guilds commands usage, I guess
20. mess around with contributing and stuff

    ### Question mark
21. Bring back opendota autoparse for people
22. explore twitch chat bot thing
23. clips twitch check
24. include context menu commands into help menu somehow idk
25. add image name for convert thing (check resolution too 112)
26. maybe create a help web page with github web pages

    ### Last Box
27. abandon not scored game for match history
28. reaction roles with new selects
29. clip twitch check
30. rewrite purge into something better
31. custom server name for dotafeed feature
32. solve twitter somehow idk fok - probably reload the whole extension
33. ??? cmlist when signing in into steam
34. unsolved mystery [0] x30
35. async dota 2 client but really i only need async wait_for
