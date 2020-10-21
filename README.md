# ziBot

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
- Create a file named `config.json` with this format:
```json
{
    "bot_token": "YOUR-TOKEN-HERE",
    "twitch": {
        "id": "",
        "secret": ""
    },
    "reddit": {
        "id": "",
        "secret": "",
        "user_agent": "ziBot/0.4"
    },
    "openweather_apikey": ""
}
```
- Launch the bot with ```python3 main.py```

## TODOs
[Click here](https://github.com/null2264/ziBot/projects) to see all the plan i have for this project.

## License
[GNU GPL-3.0-or-later](https://github.com/null2264/ziBot/blob/master/LICENSE)
