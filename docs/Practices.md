# Practices

In this file I will advice some code practices to keep some *specific* things that aren't handled automatically by a formatter/linter consistent across the repository.
Frankly, this document is a little bit over-doing, but hey, sometimes things like this bother me.

## 0. Table of Content

* [Practices](#practices)
  * [0. Table of Content](#0-table-of-content)
  * [2. `discord.Embed` order](#2-discordembed-order)
  * [3. Game namings](#3-game-namings)
  * [4. Doc Strings](#4-doc-strings)
    * [4.1. Sources](#41-sources)
    * [4.2. Why do they put extra space in type hints?](#42-why-do-they-put-extra-space-in-type-hints)
    * [4.3. Docs String Emotes](#43-docs-string-emotes)
  * [Error Handler Embeds](#error-handler-embeds)
  * [Random Standards](#random-standards)
  * [How to use Timers](#how-to-use-timers)

## 2. `discord.Embed` order

Keep the order of methods/parameters the same as "visual" order in Discord App's UI from top-left -> bottom-right. PS. Remember to use `color` over `colour` due to tip #1. <!-- cSpell: ignore colour --> Example:

```py
embed = (
    discord.Embed(
        color=discord.Color.blue(),
        title="Test",
        url="https://www.google.co.uk/"
        description="Test Description",
    )
    .set_author(name="Name", icon_url="")
    .set_thumbnail(url="thumbnail")
    .set_image(url="image")
    .set_footer(text="Text")
)
```

## 3. Game namings

<!-- # TODO: maybe change this? just write 2 everywhere -->

| Game         | Dota 2                    | League of Legends             |
| ------------ | --------------------------|------------------------------ |
| Display Name | Dota 2                    | League of Legends             |
| snake_case   | `.dota`, `dota_hero`, ... | `.lol`, `lol_champion`, ...   |
| CamelCase    | `Dota`, `DotaClient`, ... | `League`, `LeagueClient`, ... |

* I don't like writing "2" in any variations of "Dota 2" writing for any Python definitions.
* For League of Legends, using `Lol` or `LoL` for class names just feels ridiculous (while `lol` is fine for `snake_case` variables). So let's go with `League`. Consistent inconsistency, smh.

## 4. Doc Strings

This is a big one. While I have chosen to follow Numpy doc style guide:  <https://numpydoc.readthedocs.io/en/latest/format.html> - I have a lot of problems with it. Generally, It doesn't really matter if we go away from the format as we don't use "readthedocs" services or anything like that. As long as we stay consistent within the project and my eyes are happy - we good.

### 4.1. Sources

Let's start with a thing that is missing from the NumPy guide but I want these sections to exist within the repository.

Numpy doesn't have such section in their standard but "borrowing" code is a very common practice and if the function/class is majorly inspired/copy-pasted I like to acknowledge the original sources in the doc string right away.

Template:

```py
"""
Sources
-------
* Name of the source: extra pointers (license)
    https://link_to_the_source.com

    Some extra information.
"""
```

Example:

```py
"""
Sources
-------
* Rapptz/RoboDanny: `plural` class (license MPL v2)
    https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/formats.py

    This class is very nice.
"""
```

### 4.2. Why do they put extra space in type hints?

This is where I do the doc-strings differently. I don't know why numpy-docs recommend this, but do not do this.

Numpy format:

```py
"""
Parameters
----------
event : str
"""
```

do this, which is pretty much plain copy-paste of the function signature:

```py
"""
Parameters
----------
event: str
"""
```

Very simple to maintain - simply copy-paste the signature. In the same fashion, I don't do their `default=` or `, optional` advice, once again, just copy paste the whole signature `event: str = "wow"` and not `event: str, default="wow"`. We aren't building doc web pages here. To be honest, we should just remove all Doc linters from Ruff.

### 4.3. Docs String Emotes

In slash commands' doc-strings I like to use emotes for some flavour and color so it looks a bit better in Discord UI when browsing slash menu.

* Use actual unicode characters, i.e. "🎸" in the beginning of doc strings for app commands. This way it's much easier to Ctrl+F for whether it was already used by another command. This is because in all other places we use `N{}` versions of those (such as `N{GUITAR}`).

## Error Handler Embeds

Pseudo code:

```py
discord.Embed(
    color="Some shade of red",
    title=(
        "*Task/Event/Ctx Command/App Command/etc* Error: "  # note the colon : and space
        "`*display name*, i.e. Class name for Views/Tasks or display name for commands`",  # note the backticks `
    ) 
    url=""  # ???
    description="",  # ???
)
.set_author(
    name="@User in #Channel (Guild Name)",  # or DM Channel if it's DM. 
    icon_url="@User's avatar"
)
# .set_thumbnail(url="")  # None, because it takes away the space
.add_field(name="Args if Any"),  # use `ps` code language
.add_field(name="Kwargs if Any"),# use `ps` code language
.add_field(name="Snowflake IDs if Any"), # use `ebnf` code language
# .set_image(url="")  # None, because what to put there?
.set_footer(
    text=f"class_name.function_name for non-commands OR function_name: display_name for commands", # note that this goes to logger by default; Class name can be skipped if it's too obvious, i.e. ctx/app commands.
    icon_url="Guild Icon",  # @User avatar if it's DM
)
```

As we can see `url` and `description` are undecided.

## Random Standards

* Write `# type: ignore[reportReturnType]` and not `# pyright: ignore[reportReturnType]`
* add two empty lines before `__all__` which should be there right after `if TYPE_CHECKING`

## How to use Timers

```py
    @commands.Cog.listener("on_birthday_timer_complete")
    async def birthday_congratulations(self, timer: Timer[BirthdayTimerData]) -> None:
        # something something
        await self.bot.timers.cleanup(timer.id)  # ! This is a must 
```
