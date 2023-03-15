"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from discord.ext.commands.errors import CommandError


class CCException(CommandError):
    pass


class CCommandNotFound(CCException):
    def __init__(self, name: str = "Unknown") -> None:
        super().__init__("Command '{}' not Found!".format(name))


class CCommandAlreadyExists(CCException):
    def __init__(self, name: str = "Unknown") -> None:
        super().__init__("A command/alias called `{}` already exists!".format(name))


class CCommandNotInGuild(CCException):
    def __init__(self, name: str = "Unknown") -> None:
        super().__init__("Custom command only available in guilds")


class CCommandNoPerm(CCException):
    def __init__(self, name: str = "Unknown") -> None:
        super().__init__("You have no permissions to use this command")


class CCommandDisabled(CCException):
    def __init__(self, name: str = "Unknown") -> None:
        super().__init__("This command is disabled")
