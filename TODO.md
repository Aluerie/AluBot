### Current thoughts
1. routing thing for league
2. research star thing *roles
3. request_matchmaking_stats()
4. add some difference between league and dota database add logs, icon I guess
5. edge cases when people delete channels/guilds
6. async sqlalchemy and idk research better code/approach - maybe subclass database classes ?
7. look at every cog in robo danny/pycord manager/stella
8. rewrite purge into something better
9. abandon not scored games for match history
10. DPC ranking command, Dpc points too
11. make muted by who into logs
12. we might want to move image utils into `bot` subclass bcs of session weirdness
13. context menu commands into help menu somehow idk
14. clips twitch check
15. embed builder - editor - context menu
16. text for dota lol embeds went down
17. custom server name for dotafeed feature
18. add league account check to league after we rewrite it a bit better
19. make blocked words league to be a command that takes/writes rules into dataabase

### Fix Later
1. ?tag emoji escapes 
2. add image name for convert thing (check resolution too 112)
maybe make error original for conversion error as well rom converters


### New Features
1. nsfw functions

### Steal feature
1. My own starboard | CarlBot 
2. My own polls | Poolmaker Bot

### Future
1. twitch stream live proper listener when twitch releases it
2. add "all" key into heroes so all heroes can be traced

### IMPROVE
1. `map` usages
2. remove `regex` library in favour of `re`
3. remember `a[start:stop:step]` so `a[::-1]` is reverse
4. ?tag learn async
5. learn collection lib
6. ?tag eval
7. make a few server with emotes for more interesting #emotespam or maybe even code feature where bot make some guilds and populates them with emotes
8. research TypeVar stuff
9. remember if we ever have embed limit problems we can shorten emotes into `<:_:id> instead of <:name:id>` (need to check if it works)