**WARNING:** This branch is a rewrite of ziBot and not yet ready to be used, use [master branch](https://github.com/ZiRO-Bot/ziBot/tree/master) instead!

`config.py` file example [**REQUIRED!**]

```py
token="bottokengoeshere"
# Database URL, planned to be working with any sql
# (using https://github.com/encode/databases/ and SQLAlchemy Core)
# URL Examples:
# - sqlite:///database.db
# - postgresql://localhost/example?ssl=true
# - mysql://localhost/example?min_size=5&max_size=20
sql="sqlite:///database.db"
```

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
