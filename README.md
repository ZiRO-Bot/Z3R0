`ziBot (ZiRO's Bot)`
--------------------

A **free** and **open-source** multi-purpose discord bot.

**WARNING:** This branch is a rewrite of ziBot and not yet ready to be used, use [master branch](https://github.com/ZiRO-Bot/ziBot/tree/master) instead!

`config.py` file example [**REQUIRED!**]

```py
token="YOUR BOT TOKEN GOES HERE"

# Database URL (using https://github.com/encode/databases/ and SQLAlchemy Core)
# NOTE: Query is created for sqlite, be sure to edit `exts/utils/dbQuery.py` for other SQL!
#
# URL Examples:
# - sqlite:///database.db
# - postgresql://localhost/example?ssl=true
# - mysql://localhost/example?min_size=5&max_size=20
sql="sqlite:///database.db"
```

### Overhaul changes

- [**Rename**] `cogs/` -> `exts/`
- [**New**] Command priority [0: Built-in, 1: Custom]
- [**New**] Use databases to handle SQL (Edit `exts/utils/dbQuery.py` if you're planning to use other SQL instead of  `sqlite`!)

### Overhaul Plan

- User-made command system, allow user to make command that act similarly to built-in commands.
- Integrate user-made commands into help commands.
- Secondary prefix that prioritize user-made commands over built-in commands.
- Complete moderation command rewrite.
- Command manager, disable and enable both built-in and user-made command (built-in is the priority).
- Filter to show/hide user-made command for help commands.
- Built-in category for user to categorized their commands.
- Public/Private commands, allowing other user to use each other's command in a different server.
- Relicense (Migrate from GPLv3)

### License

Public Domain (Not specified yet.)
