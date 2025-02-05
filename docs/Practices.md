# Practices

In this file I will list common code practices (mostly small ones) such as

* naming
* order
to keep things consistent.

Just some things that do not get handled automatically by Black/Ruff.

## `discord.Embed` order

Mostly same as its own parameters and "visual" order in Discord App from top-left -> bottom-right diagonal.

```py
embed = (
    discord.Embed(
        colour=discord.Colour.blue(),
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

## Dota 2 namings

<!-- # TODO: maybe change this? just write 2 everywhere -->

* if it's a display name then we write "2", i.e. `"Dota 2"`
* if it's not then do not write the number, i.e. `self.bot.dota`. Idk, I just don't like how things like `dota2_hero` look like.

## Docs

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

## Random Standards

* Write `# type: ignore[reportReturnType]` and not `# pyright: ignore[reportReturnType]`
* add two empty lines before `__all__` which should be there right after `if TYPE_CHECKING`
