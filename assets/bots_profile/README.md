# 🎭 Bot's Profile Assets

## 👮 Copyright

I'm using assets from a default Telegram Sticker Pack MiladyNoir:

* Link: <https://t.me/addstickers/MiladyNoir>
* All credits to Telegram

## 🖊️ Note to myself how to update the bot's profile

At the time, the developer portal didn't support uploading gifs. However, you still could upload animated avatars/banners via API directly or with the help of `discord.py`.

So this is how I did with `jishaku`:

### 🖼️ Avatar

$jsk py

```py
with open("./assets/bots_profile/avatar.gif", "rb") as f:
    await bot.user.edit(avatar=f.read())
```

### 🎋 Banner

$jsk py

```py
with open("./assets/bots_profile/banner.gif", "rb") as f:
    await bot.user.edit(banner=f.read())
```
