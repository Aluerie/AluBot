# Tips

Just some things that I keep forgetting.

1. In hybrid commands to make autocomplete work we need to use `Transform`:

```py
def hybrid(ctx: Context, timezone: app_commands.Transform[TimeZone, TimeZoneTransformer])
```

In app commands we need to use it like that^ to make it work at all
