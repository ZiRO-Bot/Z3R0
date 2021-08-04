# 3.1.0

- [**New**] Re-added someone command (mimicking `@someone` April Fools command
  from discord) but only available on April Fools!
- [**Improved**] **Behind the scene**: Use pre-commit to run isort and black
  before committing changes
- [**Improved**] **Behind the scene**: Replace requirements.txt with poetry
- [**Improved**] **Behind the scene**: Use flake8 (pyproject-flake8) and
  pyright
- [**New**] Added anti mute evasion
- [**Improved**] Alongside anti mute evasion, newly binded/set mute role will
  merged with old mute rule (added automatically to muted members)
- [**Changed**] Splitted `>command set` and `>command edit` (prevent accidental `set content`)
- [**New**] Finally added functionality to `>command set category`
- [**New**] Added Image category and re-added triggered
- [**New**] Added blurplify
- [**Improved**] Added `filters` flag to help command
- [**Improved**] `>command set mode` success message now show mode's description

# 3.0.5

- [**Fixed**] Fix `CCommandNoPerm` not being handled by error handler

# 3.0.4

- [**Fixed**] Fix google search's safe search not working

# 3.0.3

- [**Fixed**] Fixed more issue with Google search throwing error when there's
  unsupported "special" results
- [**Improved**] Google search now supports Currency converter
- [**New**] Added cooldown for Google search to avoid abuse (1 per 10 seconds,
  per user)

# 3.0.2

- [**Changed**] **Behind the scene**: Replace cse with google search web scrape
  (gives better result but have higher chance of breaking)

# 3.0.1 (Hotfix)

- [**Fixed**] `1m spam` parsed as `1m s` and `pam` instead of `1m` and `spam`
- [**Improved**] You can now check required perms to execute a command inside
  help command
- [**New**] Added `>command mode` and `>command modes` to check custom command
  current mode and all different modes for custom command

# 3.0.0 (Overhaul)

- [**Rename**] `cogs/` -> `exts/`
- [**New**] Command priority [0: Built-in, 1: Custom]
- [**New**] Use databases to handle SQL (Edit `exts/utils/dbQuery.py` if you're
  planning to use other SQL instead of  `sqlite`!)
- [**Rename**] `ziBot` -> `Z3R0`
- [**New**] Mascot, named `Z3R0`
- [**Relicense**] `GPL-3.0` -> `MPL-2.0`
- [**Fixed**] Priority doesn't work on user-based input (string, int, etc)
- [**New**] "Colour Information" command
- [**New**] `Timer` ext
- [**Improved**] Temporary ban using the new `Timer` ext
- [**Improved**] Guild data will countdown up to 30 days before deleting when
  the bot leave the guild instead of instantly deleting the data
- [**Improved**] Prefixes now separated to custom and built-in/default (bot
  mention and `>` by default)
- [**Changed**] Split greeting, now its possible to have farewell and welcome
  message in separate channel
- [**Improved**] `>command disable` and `>command enable` will now try to
  disable/enable built-in command by default if you're a guild moderator
- [**Improved**] Changed POSIX-style flags `--channel #channel-mention` to
  Discord-style flags `channel: #channel-mention`, following dpy v2.0 flag
  behaviour
- [**Improved**] Temporary mute using the new `Timer` ext
- [**Improved**] Translate's destination language now adjustable instead of
  hardcoded to `en` (source language are detectable, but you can specify it by
  writing `ja->id`)
- [**Improved**] **Behind the scene**: Better roll dice handling
