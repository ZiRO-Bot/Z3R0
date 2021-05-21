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
</p>

## Configuration

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

## Overhaul

### Overhaul changes

- [**Rename**] `cogs/` -> `exts/`
- [**New**] Command priority [0: Built-in, 1: Custom]
- [**New**] Use databases to handle SQL (Edit `exts/utils/dbQuery.py` if you're planning to use other SQL instead of  `sqlite`!)
- [**Rename**] `ziBot` -> `Z3R0`
- [**New**] Mascot, named `Z3R0`

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
- Better way of handling temp ban/mute
- Migration tool, migrate from old database "layout" to newer "layout"
- i18n (If possible)

## License

Public Domain (Not specified yet.)
