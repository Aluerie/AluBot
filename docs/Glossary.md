# Glossary

Just some glossary so that I try to keep consistent terminology across the project since many discord.py related denominations can be described by multiple terms.

## Terminology

* `ntr`
    my shortcut for `interaction`. Everybody calls `Context` as `ctx` so I thought to make 3 letter abbreviation for interaction as well, since it's also used in 90% of functions.
* txt command [txt cmd]
    Text/prefix command. The command that is getting invoked via typing message like `$help`.
* app command [app cmd]
    Slash/context menu command. These take `ntr` of type `discord.Interaction` as their context-argument.
* hybrid command [hyb cmd]
    These commands are made with `@commands.hybrid_command`. They make both txt and app commands in one go if the code structure/signature allow it.
* ctx command
    `ctx` based command. This includes both txt commands and hybrid commands because they take `ctx` of type `AluContext` as their context-argument.

## Notes

I don't really know where to put it. Maybe I shouldn't write it at all. But here some examples of using these namings.

* `ctx_cmd_errors` is called like this because it's getting called when error is raised in "ctx command" meaning both hybrid and txt commands.
* `utils.checks` submodules are called `app`, `txt`, `hybrid` to showcase the difference too.
