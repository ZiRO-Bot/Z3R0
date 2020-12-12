# ziBot

[![Discord Bots](https://top.gg/api/widget/status/740122842988937286.svg)](https://top.gg/bot/740122842988937286)

**Python 3.8.x or higher is required!** 

A multi-purpose customizable open-source discord bot.

A fork of mcbeDiscordBot (Steve the bot) that rewritten to be able to operate on multiple server. Some code are translated mee6's old deprecated codes that rewritten and some are messy js to python translation.

## Dependencies
To install the dependencies, you can use this command:
```
# Linux
python3 -m pip install -r requirements.txt

# Windows
py -3 -m pip install -r requirements.txt
```

## Usage
*Hosting ziBot on your own server is recommended!*
### User (Limited Control)
- [Invite](https://discord.com/api/oauth2/authorize?client_id=740122842988937286&permissions=470153334&scope=bot) ziBot to your server
- Set necessary variable using `>channel set` and `>prefix` command

### Host (Full Control)
- Create folder called `data` (to prevent error)
- Create a file named `config.py` inside a folder named `core` with this format:
```python
token = "TOKEN_GOES_HERE!"
twitch = {
    "id": "", "secret": ""
}
reddit = {
    "id": "",
    "secret": "",
    "user_agent": "ziBot/0.1",
}
openweather_apikey = ""
postgresql = "postgresql://username:password!@hostname/database"
```
- Launch the bot with ```python3 main.py```

## Translation
All translation file located in `locale/` directory,

ziBot uses [zi-i18n](https://github.com/ZiRO-Bot/zi-i18n) as its Internationalization system.

Example:
```python
# Specification/Formatting: <!bot[.cogs_name].[translation_name] "Translated stuff goes here">
<!bot.utility.searx "Mencari `{keyword}`">
# Output: Mencari `{keyword}`
```

## TODOs
[Click here](https://github.com/null2264/ziBot/projects) to see all the plan i have for this project.

## License
[GNU GPL-3.0-or-later](https://github.com/null2264/ziBot/blob/master/LICENSE)
