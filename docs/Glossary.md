# Glossary

Just some glossary so that I try to keep consistent terminology across the project since many discord.py related denominations can be described by multiple terms.

## Terminology, short-words and abbreviations

* **prefix command**

    Text/prefix command. The command that is getting invoked via typing message like `$help`.
* **app command [app cmd]**

    Slash/context menu command. These take `ntr` of type `discord.Interaction` as their context-argument.
* **hybrid command**

    These commands are made with `@commands.hybrid_command` decorator. They make both `prefix` and `app` commands in one go if the code structure/signature allow it.
* **ctx command**

    `ctx` based command. This includes both txt commands and hybrid commands because they take `ctx` of type `AluContext` as their context-argument.
* **community**

    The discord server for Aluerie's community. Some features of the bot are specifically designed for it.
* **hideout**

    My personal one-man discord server. I do most of the testing here. Also some features of the bot are specifically designed for it.
* **context menu**

    In docs it's called `app_commands.ContextMenu`, so I guess we have to suffer with this. We have so much meaning to the word `ctx` connected to `Context` related-stuff defined above that it doesn't make sense to call this "ctx menu", so let's call it "context menu" as in full words.

## Notes

But here some examples of using these namings.

* `ctx_cmd_errors` is called like this because it's getting called when error is raised in "ctx command" meaning both hybrid and txt commands.
* `utils.checks` submodules are called `app`, `prefix`, `hybrid` to showcase for which exact type of commands they are made for.
