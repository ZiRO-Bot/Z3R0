<p align="center">
    <!-- Change the img source to Z3R0 logo/mascot when its done --->
    <a href="https://github.com/ZiRO-Bot/ziBot"><img src="/assets/img/banner.png" alt="Z3R0" width="720"/></a>
</p>

<h1 align="center"><code>Z3R0 (formerly ziBot)</code></h1>

<h3 align="center"> A <b>free</b> and <b>open-source</b> multi-purpose discord bot. </h3>

<p align="center">
    <b>WARNING:</b> This branch is a rewrite of ziBot and not yet ready to be used, use <a href="https://github.com/ZiRO-Bot/ziBot/tree/master">master</a> branch instead!
</p>

<p id="badges" align="center">
    <a href="https://top.gg/bot/740122842988937286"><img src="https://top.gg/api/widget/status/740122842988937286.svg"></a>
    <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
    <a href="/LICENSE"><img alt="License: MPL-2.0" src="https://img.shields.io/badge/license-MPL--2.0-blue.svg"></a>
</p>

## About

**`Z3R0`** (formerly **`ziBot`**) is a **free** and **open-source** multi-purpose discord bot, created for fun in the middle of quarantine. Used to be fork of [Steve-Bot](https://github.com/MCBE-Speedrunning/Steve-Bot) by MCBE Speedrunning Moderators.

### Features

- Custom Command, allow your mods or member to create a custom command
Coming Soon.

## Configuration

### Quick Setup

Not ready yet.

### Self-Hosting

- Install all the dependencies by executing this command,

   ```zsh
   # Windows
   py -m pip install -r requirements.txt

   # Linux
   python3 -m pip install -r requirements.txt
   ```

- Copy and paste (or rename) [`config.py-example`](./config.py-example) to `config.py`
- Edit all the necessary config value (`token`, `botMasters`, and `sql`)
- Run the bot by executing this command,

   ```zsh
   # Windows
   py main.py

   # Linux
   python3 main.py
   ```

## Overhaul

### Changelog

Moved to [CHANGELOG.md](./CHANGELOG.md)

### Overhaul Plan

- Perm indicator inside help command
- Cooldown
- Migration tool, migrate from old database "layout" to newer "layout"
- Image manipulation (Filter and stuff) (in `v3.0.1` maybe?)
- Re-implement/improve old (`v2.x`) commands to `v3.0.0`
- Event for banned member, ~~member boosting a guild~~ (Just need to implement setup for it), and muted member
- Add case log (in `v3.0.1` maybe?)
- Properly support different SQL scheme (databases have `database_url.scheme` to check scheme type) (in `v3.0.1` maybe?)
- Tags (stripped version of custom command)
- Unify categories/exts emoji

### Pending Plan

> Waiting for Dpy `v2.0` to release
- Slash command (Waiting for Dpy `v2.0`)
- ~~Integrate user-made commands into help commands~~
- ~~Add flags ('--something', also waiting for Dpy `v2.0`)~~
   - ~~Replace more POSIX-style flags with Discord-style flags~~
   - Use flags from Dpy `v2.0` when it released
   - Filter to show/hide user-made command for help commands using flags

### Scrapped Plan

> Plan that unfortunately not possible (atleast for now)
- Music Player
- Public/Private commands, allowing other user to use each other's command in a different server.
- Twitch and YouTube notification (Maybe?)
- i18n (If possible)

## License

This bot is licensed under [**Mozilla Public License, v. 2.0 (MPL-2.0)**](/LICENSE)
