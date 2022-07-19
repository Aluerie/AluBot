### Current thoughts

1. write descriptions for commands and params for dota, league- commands
2. flags for league accounts, literal for league regions
4. 
---
---
---
3. Rewrite all twitch stuff in a way we depend on twitch ids and not names,
4. Think about help command thing "mods only"
5. make muted by who into logs

6. async sqlalchemy
7. sort out total garbage in utils folder
8. look at every cog in robo danny/pycord manager/stella
9. rewrite purge into something better
10. abandon not scored games for match history
11. DPC ranking command, Dpc points too
12. look into 5.3.2 pyot update - Change the Lock on ChampionKeysCache to SealLock, as the asyncio.Lock requires an event loop at the moment of instantiation, an issue that may be encountered by non-async "tasks explorers".

### Immediate fix
2. ?tag button cooldown
3. ?tag emoji escapes 
4. add image name for convert thing (check resolution too 112)
maybe make error original for conversion error as well rom converters
5. Feature to download images From Twitter 

### New Features
5. nsfw functions

### Probably Garbage
7. edit dota and league messages after match ends to include some stats like KDA items victory-lose, RunesReforged, player names, proplayers etc

### Steal feature
12. My own starboard | CarlBot 
13. My own polls | Poolmaker Bot

### Future
15. twitch stream live proper listener when twitch releases it

### IMPROVE
16. `map` usages
17. remove `regex` library in favour of `re`
18. async sqlalchemy asyncsession ? and also subclass your database like normal human being
19. remember `a[start:stop:step]` so `a[::-1]` is reverse
20. ?tag learn async
22. learn collection lib
23. ?tag eval
24. make a few server with emotes for more interesting #emotespam or maybe even code feature where bot make some guilds and populates them with emotes
25. research TypeVar stuff
26. remember if we ever have embed limit problems we can shorten emotes into `<:_:id> instead of <:name:id>`