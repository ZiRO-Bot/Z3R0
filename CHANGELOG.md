# 3.0.0 (Overhaul)

- [**Rename**] `cogs/` -> `exts/`
- [**New**] Command priority [0: Built-in, 1: Custom]
- [**New**] Use databases to handle SQL (Edit `exts/utils/dbQuery.py` if you're planning to use other SQL instead of  `sqlite`!)
- [**Rename**] `ziBot` -> `Z3R0`
- [**New**] Mascot, named `Z3R0`
- [**Relicense**] `GPL-3.0` -> `MPL-2.0`
- [**BugFix**] Priority doesn't work on user-based input (string, int, etc)
- [**New**] "Colour Information" command
- [**New**] `Timer` ext
- [**Improved**] Temporary ban using the new `Timer` ext
- [**Improved**] Guild data will countdown up to 30 days before deleting when the bot leave the guild instead of instantly deleting the data
- [**Improved**] Prefixes now separated to custom and built-in/default (bot mention and `>` by default)
- [**Changed**] Split greeting, now its possible to have farewell and welcome message in separate channel
- [**Improved**] `>command disable` and `>command enable` will now try to disable/enable built-in command by default if you're a guild moderator
- [**Improved**] Changed POSIX-style flags `--channel #channel-mention` to Discord-style flags `channel: #channel-mention`, following dpy v2.0 flag behaviour
- [**Improved**] Temporary mute using the new `Timer` ext
- [**Improved**] Translate's destination language now adjustable instead of hardcoded to `en` (source language are detectable, but you can specify it by writing `ja->id`)
- [**Improved**] **Behind the scene**: Better roll dice handling