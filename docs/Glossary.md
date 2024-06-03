# Glossary

Just some glossary so that I try to keep consistent terminology across the project since many discord.py related denominations can be described by multiple terms.

## Terminology, short-words and abbreviations

* **ntr**

    Short for `interaction`. This is rarely used. Mostly leftover for stuff like `ctx_ntr` so it doesn't look as ridiculous as `ctx_interaction`. I used to have it as a general 3 letters abbreviation for interactions so it's like `ctx` for context, but we went away from this idea "to be like everybody else" because it's more readable.

* **prefix command**

    Text/prefix command. The command that is getting invoked via typing message like `$help`, those commands are made with `@commands.command` decorators and such.

* **app command [app cmd]**

    Slash/context menu command. These take `interaction` of type `discord.Interaction` as their context-argument.

* **hybrid command**

    These commands are made with `@commands.hybrid_command` decorator. They make both `prefix` and `app` commands in one go if the code structure/signature allow it.

    Example for three terms above: `utils.checks` submodules are called `app`, `prefix`, `hybrid` to showcase exact type of commands they are made for.

* **ctx command**

    `ctx` based command. This includes both txt commands and hybrid commands because they take `ctx` of type `AluContext` as their context-argument.

    Example: `ctx_cmd_errors` is called like this because it's getting called when error is raised in both hybrid and txt commands.

* **context menu**

    In docs it's called `app_commands.ContextMenu`, so I guess we have to suffer with this. We have so much meaning to the word `ctx` connected to `Context` related-stuff defined above that it doesn't make sense to call this "ctx menu", so let's call it "context menu" as in full words.

* **community**

    The discord server for Aluerie's community. Some features of the bot are specifically designed for it.
* **hideout**

    My personal one-man discord server. I do most of the testing here. Also some features of the bot are specifically designed for it.

## Chosen PIL notations

We might go back to full words in pillow but specifically in pillow it feels right to use short notations with index-like underline notations, i.e. "facet_h" where h represents "height".

* **x, y, u, v**

    Notation for the `(top_left_x, top_left_y, bottom_right_x, bottom_right_y)` tuple. Simple 4 letters is just nicer to look at. I.e. `picture_u` means coordinate for its `bottom_right_x`

* **h, w**

    Notation for height, width, i.e. `picture_w` means picture width.

* **p**

    Padding, i.e. `picture_p` means padding of the picture.

* **canvas**

    Similarly to IRL canvas - it's just a drawing board for us (the artist :o). We draw on this canvas.
