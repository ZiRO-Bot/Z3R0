# ziBot

**Python 3.8.x or higher is required!**

Just a fork of mcbeDiscordBot but rewritten a bit. Some code are translated mee6's old deprecated codes and some messy translated js to python codes that works on the new version of [discord.py](https://github.com/Rapptz/discord.py)

## Dependencies
- [discord.py](https://github.com/Rapptz/discord.py)
- youtube-dl

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
- Specify your token:
  + Create a new file called `.env` and put in your token like `TOKEN = 'YOUR_TOKEN_HERE'`
  + Set an environment variable called `TOKEN`
- Launch the bot with ```python3 zibot.py```

## TODOs
[Click here](https://github.com/null2264/ziBot/projects) to see all the plan i have for this project.
