<p align="center">
    <!-- Change the img source to Z3R0 logo/mascot when its done --->
    <a href="https://github.com/ZiRO-Bot/ziBot"><img src="/assets/img/banner.png" alt="Z3R0" width="720"/></a>
</p>

<h1 align="center"><code>Z3R0 (formerly ziBot)</code></h1>

<h3 align="center"> A <b>free</b> and <b>open-source</b> multi-purpose discord bot. </h3>

<p id="badges" align="center">
    <a href="https://top.gg/bot/740122842988937286"><img src="https://top.gg/api/widget/status/740122842988937286.svg"></a>
    <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
    <a href="https://pycqa.github.io/isort"><img alt="Imports: isort" src="https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336"></a>
    <a href="/LICENSE"><img alt="License: MPL-2.0" src="https://img.shields.io/badge/license-MPL--2.0-blue.svg"></a>
    <a href="https://liberapay.com/ZiRO2264/donate"><img alt="Donate using Librepay" src="https://img.shields.io/liberapay/patrons/ZiRO2264.svg?logo=liberapay"></a>
</p>

## About

**`Z3R0`** (formerly **`ziBot`**) is a **free** and **open-source** multi-purpose discord bot, created for fun in the middle of quarantine. Used to be fork of [Steve-Bot](https://github.com/MCBE-Speedrunning/Steve-Bot) by MCBE Speedrunning Moderators.

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

> **NOTE**: Python 3.8+ is required to host this bot!

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

  # sqlite
  poetry install --no-dev -E sqlite

  # postgresql (Using aiopg instead of ayncpg)
  poetry install --no-dev -E "postgresql+aiopg"
  ```
- Copy and paste (or rename) [`config.py-example`](./config.py-example) to `config.py`
- Edit all the necessary config value (`token`, `botMasters`, and `sql`)
- Run the bot by executing this command, `poetry run python main.py`
- If everything is setup properly, the bot should be online!

### Development

- Install poetry `pip install poetry` then run `poetry install`
- Run `poetry run pre-commit install`
- To run the bot executing this command, `poetry run python main.py`

## Overhaul

### Changelog

Moved to [CHANGELOG.md](./CHANGELOG.md)

### Overhaul Plan

- Event for ~~member boosting a guild~~ (Just need to implement setup for it)
- Add case log (in `v3.2.0` maybe?)
- Properly support different SQL scheme (databases have `database_url.scheme` to check scheme type) (in `v3.2.0` maybe?)
- Tags (stripped version of custom command)
- Unify categories/exts emoji
- Channel manager commands
- Anime (using AniList API) commands
- Reaction Role
- Starboard
- Slash command (Waiting for implementation)
- Use flags from Dpy `v2.0` when it released (In progress)
   - Filter to show/hide user-made command for help commands using flags
     (Current design: `>help category filters: custom` will only show custom command in that category)

### Pending Plan

- i18n using gettext (Learning how gettext works)

### Scrapped Plan

> Plan that unfortunately not possible (atleast for now)
- Music Player (ffmpeg+ytdl vs lavalink?)
- Public/Private commands, allowing other user to use each other's command in a different server.
- Twitch and YouTube notification (Find how to refresh webhook thingy reliably)

## License

This bot is licensed under [**Mozilla Public License, v. 2.0 (MPL-2.0)**](/LICENSE)
