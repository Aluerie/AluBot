# Practices

In this file I will list common code practices (mostly small ones) such as

* naming
* order
to keep things consistent.

Just some things that do not get handled automatically by Black/Ruff.

## `discord.Embed` order

Mostly same as its own parameters and "visual" order in Discord App from top-left -> bottom-right diagonal.

Also use `color` keyword and `discord.Color` namings.
We prefer american english as a standard in code and british for display names reasons.

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

## Game namings

<!-- # TODO: maybe change this? just write 2 everywhere -->

* if it's a display name then we write "2", i.e. `"Dota 2"`
* if it's not then do not write the number, i.e. `self.bot.dota`. Idk, I just don't like how things like `dota2_hero` look like.
* For League of Legends - use `Lol` / `lol` everywhere. Don't say `LoL` as in capital-lower-capital case. And don't use `League` because no need to confuse yourself.

## Doc Strings

Everything is covered well in numpy doc-style guide:
<https://numpydoc.readthedocs.io/en/latest/format.html#examples>.

Except for a few things that I want to consistently document myself:

### Sources

Numpy doesn't have such section in their standard but "borrowing" code around is a very common practice so let's acknowledge the original sources wherever possible, even if it's some small functions.

Template:

```py
"""
    Sources
    -------
    * Name of the source (license), extra pointers:
        https://link_to_the_source.com

        Some extra information.
"""
```

Example:

```py
"""
    Sources
    -------
    * Rapptz/RoboDanny (license MPL v2), `plural` class:
        https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/formats.py

        This class is nice. #TODO: write a better comment here lol.
"""
```

### Why do they put extra space in parameters?

I don't know why numpy-docs recommend this, but do not do this:

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

Also don't do their `default=` thing, just copy paste the whole signature `event: str = "wow"` and not `event: str, default="wow"`. We aren't building doc web pages here. To be honest, we should just remove all Doc linters from Ruff.

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

## Docs String Emotes

Use actual emotes in the beginning of doc strings for app commands. This way it's much easier to Ctrl+F in the whole project since in all other places we use N{} versions of those.

## Emotes in command doc strings

| Command / Group       | Emote                 |\N                        |
| --------------------- | --------------------- |------------------------- |
| /about                | globe_with_meridians  | \N{GLOBE WITH MERIDIANS} |
