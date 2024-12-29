# Glossary

Just some glossary so that I try to keep consistent terminology across the project since many discord.py related denominations can be described by multiple terms.

## Terminology, short-words and abbreviations

* **prefix command / ctx command**

    Text/prefix command. The command that is getting invoked via typing message like `$sync`, those commands are made with `@commands.command` decorators and such. After deprecating all of hybrid commands, within this project "ctx command" became equal to "prefix command".

* **app command**

    Slash/context menu command. These take `interaction` of type `discord.Interaction` as their context-argument.

* **context menu**

    In docs it's called `app_commands.ContextMenu`, so I guess we have to suffer with this. We have so much meaning to the word `ctx` connected to `Context` related-stuff defined above that it doesn't make sense to call this "ctx menu", so let's call it "context menu" as in full words.

* **community**

    The discord server for Aluerie's community. Some features of the bot are specifically designed for it.

* **hideout**

    My private one-person discord server. I do most of the testing here. Also some features of the bot are specifically designed for it.

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
