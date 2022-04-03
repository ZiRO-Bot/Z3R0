# v3.5

## 3.5.0

   **THIS UPDATE CONTAINS BREAKING CHANGES!**

- [**Improved / BREAKING CHANGES**] Changed project structure (all source file now located in `src/`)  
  This change breaks tortoise from loading, please change your models value from `core.db` into `src.main.core.db`!
- [**Improved**] **Technical**: Versioning now only handled by pyproject
- [**Changed**] **Technical**: Adapted discord.py's [asyncio changes](https://gist.github.com/Rapptz/6706e1c8f23ac27c98cee4dd985c8120)
- [**Improved**] You can now set Welcome and Farewell message using Modal
- [**Changed**] **Technical**: Splitting meta into several subcogs
- [**Fixed**] Re-enabled meme command, fixed by itself (probably aiohttp's user-agent bug)

# v3.4

## 3.4.6
- [**Fixed**] Getting 0 no longer possible on normal dice roll

## 3.4.5
- [**Fixed**] Fixed `AttributeError` trying to unmute a member that already left the server
- [**Fixed**] Fixed `IndexError` trying to get a AuditLog when AuditLogs is empty
- [**Removed**] Removed `ClientOSError` from log
- [**Removed**] Removed prettify.py/pretty, too buggy

## 3.4.4
- [**Fixed**] Fixed custom command deletion when guild deletion event dispatched
- [**Fixed**] Suppressed discord.Forbidden when bot can't access AuditLog
- [**Fixed**] Fixed `Invalid Form Body` when trying to send empty message content to purgatory

## 3.4.3
- [**Fixed**] Fixed command list always show 1 command

## 3.4.2
- [**Fixed**] Fixed `getAuditLogs`

## 3.4.1 (HotFix)
- [**Fixed**] Added missing file to git repo (`timer/_views.py`)
- [**Fixed**] Fixed "not in the list" error when it's not supposed to do that

## 3.4.0 (Database Overhaul)

- [**Improved**] Z3R0 now supports hosting using PostgreSQL or MySQL database
  via Tortoise, **migration required!**

# v3.3

## 3.3.7

- [**New**] Re-added channel mention to purgatory

## 3.3.6

- [**Fixed**] Fix command names being escaped when its not supposed to be escaped
- [**Improved**] More typehinting
- [**Fixed**] Handle invalid time (something like `10000 years`)

## 3.3.5

- [**Fixed**] Fixed `List is empty!` error not being handled

## 3.3.4

- [**Fixed**] Fixed NSFW check always returns False
- [**Fixed**] Fixed `AttributeError` when user try to ban `@everyone`
- [**Improved**] IsAprilFool now raised DefaultError instead of `Check failed`
- [**Improved**] IsRafael now raise SilentError instead of `Check failed`

## 3.3.3

- [**Improved**] Added description to `>caselogs` command
- [**Improved**] Help command now tell user when they have no usable commands

## 3.3.2

- [**Fixed**] Fixed `AttributeError`
- [**Fixed**] Fixed `discord.Forbidden` in Error Handler

## 3.3.1

- [**New**] You can now change news using a command instead of hardcoding it

## 3.3.0

- [**New**] Added realurl (get real url of a shorten url)
- [**Improved**] Added case number to modlog message
- [**Changed**] Rename `Bot.master` -> `Bot.owner_ids`
- [**Fixed**] Fix Admin commands' checks not working properly
- [**Improved**] Decrease modlog delay to 2 seconds delay
- [**Improved**] Merged `>help filter: custom` with `>command list`
- [**Changed**] `>command disable` and `>command enable` no longer uses flag,
  replaced with choice buttons when there's more than 1 type is found with
  identical name
- [**Fixed**] Anilist commands now works in DMs
- [**Fixed**] `>manga search` actually search for manga not anime
- [**Improved**] User now given choices between command and category when their
  names are conflicted
- [**Improved**] Custom command list now paginated
- [**New**] Added "compact mode" to paginator
- [**Improved**] Failed NSFW check will now properly "yell" at the executor,
  instead of yelling "Check failed!"
- [**Fixed**] Fixed caselog type `mute` being inconsistent ( [**For
  self-hoster**] sql query to fix your database: `UPDATE OR IGNORE caseLog SET
  type='mute' WHERE type='muted'`)
- [**New**] Added createdAt column to caselog ( [**For self-hoster**]: sql
  query to add this column without dropping the table `ALTER TABLE caseLog ADD
  COLUMN createdAt INTEGER DEFAULT 0`) [**NOTE**]: Old cases' time will return
  either "Unknown" or `1/1/1970`
- [**New**] Added `caselogs`/`cases` command to get moderator's cases
- [**Improved**] Modlog now log unmute and unban
- [**Disabled**] Disable `google` command (blocking the whole bot)

# v3.2

## 3.2.9

- [**Improved**] Re-added alias `emote` to `emoji` commands

## 3.2.8

- [**Fixed**] Fixed Moderation commands' checks not working properly

## 3.2.7

- [**Fixed**] Fixed help command not working in DMs
- [**Changed**] Use HTMLParser to convert HTML to Markdown instead of using
  RegEx

## 3.2.6

- [**Fixed**] Fixed modlog. Added 5 seconds delay, letting Audit Logs to update
  before sending modlog

## 3.2.5

- [**New**] Added ZView (`core/views.py`)
- [**New**] Added `Context.loading`
- [**Improved**] `findanime` merged with `anime` and `manga` as `random`
  subcommand

## 3.2.4

- [**Fixed**] Fixed anti-mute evasion

## 3.2.3

- [**Improved**] Merged `anime search` and `manga search` into 1 function
- [**Fixed**] Fixed IndexError when there's no anime/manga found

## 3.2.2

- [**Fixed**] Fixed a lot of issue with v3.2.1

## 3.2.0 (`discord.py v2.0`)

- [**Improved**] Updated `discord.py` (`v1.7.3` -> `v2.0.0`)
- [**New**] Re-added AniList category
- [**New**] Added ZMenuPagesView (ZMenu but using `discord.ui.View` instead of
  reactions)
- [**Changed**] Replace most if not all ArgumentParser-based flags with
  discord.py's FlagConverter
- [**Changed**] Changed help command behaviour, filters now only works for
  category (`>help info filters: custom built-in` will show custom commands
  first, `>help info filters: custom` will **only** show custom commands)
- [**Improved**] ZMenuPagesView's `_pageInfo` now acts like "Jump to" button
- [**Improved**] Added "Read More" button to AniList
- [**New**] Added Caselog, to keep track of your moderation records
- [**Improved**] Added Info/Stats to Custom Command's help page
- [**Improved**] Disabled command will displayed ~~crossed~~ on category
  commands' page (`>help category`)
- [**Changed**] Rename custom commands' `raw` -> `source` (but `raw` stays as
  alias for `source`)
- [**Fixed**] Fixed command disabler not working properly
- [**Fixed**] Fixed CheckFailure error handling
- [**Improved**] The bot now will tell you if you or the bot is missing some
  permissions

# v3.1

## 3.1.0

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
- [**Changed**] Splitted `>command set` and `>command edit` (prevent accidental
  `set content`)
- [**New**] Finally added functionality to `>command set category`
- [**New**] Added Image category and re-added triggered
- [**New**] Added blurplify
- [**Improved**] Added `filters` flag to help command
- [**Improved**] `>command set mode` success message now show mode's
  description
- [**New**] Added redify and polaroid to Image category
- [**Improved**] Modlog events now getch the "real moderator" when mod commands
  is used to trigger the events
- [**Changed**] Added cooldown to most of the commands, to prevent spam
- [**Improved**] Added timezone argument to time command (user timezone still
  coming soon)

# v3.0

## 3.0.5

- [**Fixed**] Fix `CCommandNoPerm` not being handled by error handler

## 3.0.4

- [**Fixed**] Fix google search's safe search not working

## 3.0.3

- [**Fixed**] Fixed more issue with Google search throwing error when there's
  unsupported "special" results
- [**Improved**] Google search now supports Currency converter
- [**New**] Added cooldown for Google search to avoid abuse (1 per 10 seconds,
  per user)

## 3.0.2

- [**Changed**] **Behind the scene**: Replace cse with google search web scrape
  (gives better result but have higher chance of breaking)

## 3.0.1 (Hotfix)

- [**Fixed**] `1m spam` parsed as `1m s` and `pam` instead of `1m` and `spam`
- [**Improved**] You can now check required perms to execute a command inside
  help command
- [**New**] Added `>command mode` and `>command modes` to check custom command
  current mode and all different modes for custom command

## 3.0.0 (Overhaul)

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
