<p align="center">
    <a href="https://github.com/ZiRO-Bot/ziBot"><img src="/assets/img/banner.png" alt="Z3R0" width="540"/></a>
</p>

<h1 align="center"><code>Z3R0 (codename ziBot)</code></h1>

<h3 align="center"> A <b>free</b> and <b>open-source</b> multi-purpose discord bot. </h3>

<p id="badges" align="center">
    <a href="https://top.gg/bot/740122842988937286"><img src="https://top.gg/api/widget/status/740122842988937286.svg"></a>
    <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
    <a href="https://pycqa.github.io/isort"><img alt="Imports: isort" src="https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336"></a>
    <a href="/LICENSE"><img alt="License: MPL-2.0" src="https://img.shields.io/badge/license-MPL--2.0-blue.svg"></a>
    <a href="https://liberapay.com/ZiRO2264/donate"><img alt="Donate using Librepay" src="https://img.shields.io/liberapay/patrons/ZiRO2264.svg?logo=liberapay"></a>
    <br/>
    <a href="https://github.com/ZiRO-Bot/Z3R0/actions/workflows/test.yml"><img alt="CI: Tests" src="https://github.com/ZiRO-Bot/Z3R0/actions/workflows/test.yml/badge.svg"></a>
    <a href="https://github.com/ZiRO-Bot/Z3R0/actions/workflows/build.yml"><img alt="CI: Nightly Build" src="https://github.com/ZiRO-Bot/Z3R0/actions/workflows/build.yml/badge.svg"></a>
</p>

## About

**`Z3R0`** (codename **`ziBot`**) is a **free** and **open-source** multi-purpose discord bot, created for fun in the middle of quarantine. Used to be fork of [Steve-Bot](https://github.com/MCBE-Speedrunning/Steve-Bot) by MCBE Speedrunning Moderators.

### Features

- Custom Command: allow your mods or member to create a custom command,  
  Custom command modes:
  - `0`: Only mods can add **and** manage custom commands
  - `1`: Member can add custom command but can only manage their own command
  - `2`: Anarchy mode!
- Flags/Options: better specify your needs by using flags! (example: `>command disable category: info` will disable all command inside Information category)
- Fun commands: games, meme and other fun stuff.
- Powerful moderation command.
- Image manipulation/filters.
- Useful utility command such as `execute` (execute python/other programming language code), `google`, `calc` / `math`, and more!

More feature coming soon!

## Configuration

### Quick Setup (Invite Hosted Bot)

[Click here to invite the bot!](https://discord.com/oauth2/authorize?client_id=740122842988937286&scope=bot&permissions=4260883702)

### Self-Hosting

> **Note**
>
> If you're planning to self-host the bot, I'll assume you already have a
> decent knowledge of Python, discord.py and hosting bot in general. I will
> **NOT** give support for basic issue such as "Where do I get bot token", "How
> to install Python", etc.
>
> Hosting from free hosting such as Heroku is not supported either! It's
> recommended to get a proper VPS/Cloud Server to host a bot.

#### Docker

- Install [Docker](https://docs.docker.com/install/) and [Docker-Compose](https://docs.docker.com/compose/install/)
- Create `docker-compose.yaml` file or use the one from [`docker/compose-examples`](../docker/compose-examples):

    ```yaml
    version: "3"

    services:
      bot:
        container_name: zibot
        image: ghcr.io/ziro-bot/z3r0:latest
        volumes:
          - "./data:/app/data"
          - "./config.py:/app/config.py"
    ```

- Then run:

    ```zsh
    docker-compose up -d
    
    # or if you want to use one of the sample yaml file
    docker-compose -f docker/compose-examples/basic/docker-compose.yml up -d
    ```

> Since 3.5.0, ziBot support environment variables, added specifically for Docker

| Env | Json | Description |
|-----|------|-------------|
| ZIBOT\_TOKEN | token | **REQUIRED**. Discord Bot's token, without it you can't run the bot at all. You can get it on https://discord.com/developers/applications |
| ZIBOT\_DB\_URL | sql | **REQUIRED**. The bot's database url. Format: `DB_TYPE://PATH_OR_CREDENTIALS/DB_NAME?PARAM1=value&PARAM2=value`, you can visit [TortoiseORM's documentation](https://tortoise.github.io/databases.html#db-url) to learn more about it |
| ZIBOT\_BOT\_MASTERS | botMasters | Separated by spaces. The bot's master(s), allows listed user(s) to execute master/dev only commands. By default it'll get whoever owns the bot application |
| ZIBOT\_ISSUE\_CHANNEL | issueChannel | Channel that the bot will use to send reported errors |
| ZIBOT\_OPEN\_WEATHER\_TOKEN | openweather | Token for OpenWeatherAPI, only required if you want to use the weather command |
| ZIBOT\_AUTHOR | author | Change the bot's author name (and tag) shown in the info command |
| **CURRENTLY NOT AVAILABLE** | links | Change the links shown in the info command |
| **CURRENTLY NOT AVAILABLE** | TORTOISE\_ORM | Advanced TortoiseORM configuration, you shouldn't touch it if you're not familiar with TortoiseORM |
| ZIBOT\_INTERNAL\_API\_HOST | internalApiHost | The bot's [internal API](https://github.com/ZiRO-Bot/RandomAPI) |
| ZIBOT\_ZMQ\_PUB | zmqPorts | Port for ZeroMQ's Publish |
| ZIBOT\_ZMQ\_SUB | zmqPorts | Port for ZeroMQ's Subscribe |
| ZIBOT\_ZMQ\_REP | zmqPorts | Port for ZeroMQ's Reply |

#### Manual

> **Warning**
>
> Python 3.10+ (3.10.9 is recommended) is required to host this bot!

- Download this repository by executing `git clone https://github.com/ZiRO-Bot/Z3R0.git`
  or click "Code" -> "Download ZIP"
- Install poetry by executing this command,

   ```zsh
   # Windows
   py -m pip install poetry

   # Linux
   python3 -m pip install poetry
   ```

- After poetry successfully installed, execute this command to install all required dependencies,

   ```zsh
   # postgresql
   poetry install --no-dev -E postgresql

   # mysql
   poetry install --no-dev -E mysql

   # mysql (Using asyncmy instead of aiomysql)
   poetry install --no-dev -E "mysql+asyncmy"
   ```

- Copy and paste (or rename) [`config.py-example`](../config.py-example) to `config.py`
- Edit all the necessary config value (`token`, `botMasters`, and `sql`)
- Run the bot by executing this command, `poetry run bot`
- If everything is setup properly, the bot should be online!

### Development

- Install poetry `pip install poetry` then run `poetry install`
- Install pre-commit then run `poetry run pre-commit install`
- Start the bot by running `poetry run bot`
- It is recommended to setup a test unit inside `src/test` when you added a new
  command, you can run the test by running `poetry run pytest -v`  
  Read [dpytest](https://dpytest.readthedocs.io/) documentation for more information

## Changelog

Go to the [release page](https://github.com/ZiRO-Bot/Z3R0/releases) to see
per-version changelog or [CHANGELOG.md](./CHANGELOG.md) for more detailed
changelog

## Plans

> **Note**
>
> Listed from highest to lowest priority

- Setup Tests using dpytest
  - Add test for every command
- Rework permissions
  - Currently:
    - Admin = Can configure bot
    - Manage Guild (and Mod role) = Can moderate using the bot
  - Planned:
    - Admin = Full access to bot (except for dev commands ofc)
    - Manage Guild (and Bot Manager role) = Can configure bot
    - Mod role = Bypass every moderator checks like Ban Member, Kick Member, etc
- Rework prefix system (currently `>` is hardcoded as default prefix, this
  prefix should be added to guild's data when that guild invited the bot)
- Event for ~~member boosting a guild~~ (Just need to implement setup for it)
- Tags (stripped version of custom command)
- Unify categories/exts emoji
- Channel manager commands
- Reaction Role (With buttons)
- Starboard
- Slash and ContextMenu commands (80% complete)
- Button-based (or Modal-based?) bot settings
- Data migration between 2 database

### Pending Plan

- i18n using gettext  
  Currently still figuring out how to actually implement gettext
- Modals  
  Too much limitation at the moment, waiting for model input types

### Scrapped Plan

> **Note**
>
> Some of these plans are not completely scrapped, some simply scrapped since
> it's not yet possible for me to do but I don't know whether or not it'll
> eventually be possible to be added

- Replace mute with the new timeout feature from Discord  
  The feature is too limited, maybe I'll add timeout command instead
- Music Player  
  Not in my top priority, and looking at how aggresive Google is towards music bots... maybe not gonna do it afterall
- Public/Private commands, allowing other user to use each other's command in a different server  
  Too complicated, might add it after I finally finish the dashboard
- Twitch and YouTube notification  
  Unreliable most of the time, sometimes return duplicates

## License

This bot is licensed under [**Mozilla Public License, v. 2.0 (MPL-2.0)**](/LICENSE)
