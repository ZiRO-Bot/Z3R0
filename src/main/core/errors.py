from typing import Any

import discord
from discord.ext.commands.errors import CommandError

from ..utils.format import formatPerms


class CCException(CommandError):
    pass


class CCommandNotFound(CCException):
    def __init__(self, name: Any = "Unknown"):
        super().__init__("Command '{}' not Found!".format(name))


class CCommandAlreadyExists(CCException):
    def __init__(self, name: Any = "Unknown"):
        super().__init__("A command/alias called `{}` already exists!".format(name))


class CCommandNotInGuild(CCException):
    def __init__(self, name: Any = "Unknown"):
        super().__init__("Custom command only available in guilds")


class CCommandNoPerm(CCException):
    def __init__(self, name: Any = "Unknown"):
        super().__init__("You have no permissions to use this command")


class CCommandDisabled(CCException):
    def __init__(self, name: Any = "Unknown"):
        super().__init__("This command is disabled")


class MissingMuteRole(CommandError):
    def __init__(self, prefix):
        super().__init__(
            "This guild doesn't have mute role set yet!\n"
            "Use `{0}mute create Muted` or `{0}mute set @Muted` to setup mute role.".format(prefix)
        )


class ArgumentError(CommandError):
    def __init__(self, message):
        super().__init__(discord.utils.escape_mentions(message))


class HierarchyError(CommandError):
    def __init__(self, message: str = None):
        super().__init__(message or "My top role is lower than the target's top role in the hierarchy!")


class MissingModPrivilege(CommandError):
    def __init__(self, missing_permissions=None, *args):
        self.missing_permissions = missing_permissions

        message = "You are missing mod privilege"
        if self.missing_permissions:
            message += " or {} permission(s) to run this commad.".format(formatPerms(self.missing_permissions))

        super().__init__(message, *args)


class MissingAdminPrivilege(CommandError):
    def __init__(self, missing_permissions=None, *args):
        self.missing_permissions = missing_permissions

        message = "You are missing admin privilege"
        if self.missing_permissions:
            message += " or {} permission(s) to run this commad.".format(formatPerms(self.missing_permissions))

        super().__init__(message, *args)


class NotNSFWChannel(CommandError):
    def __init__(self):
        super().__init__("You're only allowed to use this command in a NSFW channels!")


class DefaultError(CommandError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class SilentError(CommandError):
    def __init__(self, message: str = "idk") -> None:
        super().__init__(message)
