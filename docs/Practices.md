# Practices

In this file I will list common code practices (mostly small ones) such as

* naming
* order

to keep things consistent.

Just some things that do not get handled automatically by Black/Ruff.

## `discord.Embed` order

Mostly same as its own parameters and "visual" order in Discord App from top->down, left->right.

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
