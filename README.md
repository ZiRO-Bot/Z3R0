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

Coming Soon.

## Configuration

### Quick Setup

Not ready yet.

### Self-Hosting

- Copy and paste (or rename) [`config.py-example`](./config.py-example) to `config.py`
- Edit all the necessary config value (`token`, `botMasters`, and `sql`)

## Overhaul

### Changelog

- [**Rename**] `cogs/` -> `exts/`
- [**New**] Command priority [0: Built-in, 1: Custom]
- [**New**] Use databases to handle SQL (Edit `exts/utils/dbQuery.py` if you're planning to use other SQL instead of  `sqlite`!)
- [**Rename**] `ziBot` -> `Z3R0`
- [**New**] Mascot, named `Z3R0`
- [**Relicense**] `GPL-3.0` -> `MPL-2.0`
- [**BugFix**] Priority doesn't work on user-based input (string, int, etc)
- [**New**] "Colour Information" command
- [**New**] `Timer` ext
- [**Improved**] Temporary ban/mute using the new `Timer` ext
- [**Improved**] Guild data will countdown up to 30 days before deleting when the bot leave the guild instead of instantly deleting the data
- [**Improved**] Prefixes now separated to custom and built-in/default (bot mention and `>` by default)
- [**Changed**] Split greeting, now its possible to have farewell and welcome message in separate channel
- [**Improved**] `>command disable` and `>command enable` will now try to disable/enable built-in command by default if you're a guild moderator
- [**Improved**] Changed POSIX-style flags `--channel #channel-mention` to Discord-style flags `channel: #channel-mention`, following dpy v2.0 flag behaviour

### Overhaul Plan

- ~~Integrate user-made commands into help commands~~
- ~~Add flags ('--something', also waiting for Dpy `v2.0`)~~
   - Replace more POSIX-style flags with Discord-style flags
   - Use flags from Dpy `v2.0` when it released
   - Filter to show/hide user-made command for help commands using flags
- Complete moderation command rewrite. (Currently only ban is fully implemented)
- Migration tool, migrate from old database "layout" to newer "layout"
- i18n (If possible)
- Twitch and YouTube notification (Maybe?)
- Image manipulation (Filter and stuff)
- Re-implement/improve old (`v2.x`) commands to `v3.0.0`
- Slash command (Waiting for Dpy `v2.0`)
- Event for banned member, member boosting a guild, and muted member
- Add case log

### Scrapped Plan

> Plan that unfortunately not possible (atleast for now)
- Music Player
- Public/Private commands, allowing other user to use each other's command in a different server.

## License

This bot is licensed under [**Mozilla Public License, v. 2.0 (MPL-2.0)**](/LICENSE)
