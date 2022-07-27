### Current thoughts

non twitch players for dota

routing thing for league
1. do a research on star thing *roles
2. request_matchmaking_stats()
3. rewrite dota py into actual module(-s) i guess ?
4. make variable for api connstatans and for cdn
5. add some difference between league and dota database add logs, icon i guess
6. edge cases when people delete channels/guilds
7. async sqlalchemy
8. sort out total garbage in utils folder
9. look at every cog in robo danny/pycord manager/stella
10. rewrite purge into something better
11. abandon not scored games for match history
12. DPC ranking command, Dpc points too
13. look into Pyot updates on ChampionKeysCache
14. Rewrite all twitch stuff in a way we depend on twitch ids and not names,
15. make muted by who into logs

### Immediate fix
15. ?tag button cooldown
16. ?tag emoji escapes 
17. add image name for convert thing (check resolution too 112)
maybe make error original for conversion error as well rom converters

### New Features
18. nsfw functions

### Probably Garbage
19. edit dota and league messages after match ends to include some stats like KDA items victory-lose, RunesReforged, player names, proplayers etc

### Steal feature
20. My own starboard | CarlBot 
21. My own polls | Poolmaker Bot

### Future
22. twitch stream live proper listener when twitch releases it
23. add "all"  key into heroes so all heroes can be traced

### IMPROVE
24. `map` usages
25. remove `regex` library in favour of `re`
26. async sqlalchemy asyncsession ? and also subclass your database like normal human being
27. remember `a[start:stop:step]` so `a[::-1]` is reverse
28. ?tag learn async
29. learn collection lib
30. ?tag eval
31. make a few server with emotes for more interesting #emotespam or maybe even code feature where bot make some guilds and populates them with emotes
32. research TypeVar stuff
33. remember if we ever have embed limit problems we can shorten emotes into `<:_:id> instead of <:name:id>`