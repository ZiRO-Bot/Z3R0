class BotException(Exception):
    pass


class NotInGuild(BotException):
    def __init__(self):
        super().__init__("This command is not available in DMs!")


class CCException(BotException):
    pass


class CCommandNotFound(CCException):
    def __init__(self, name: str = "Unknown"):
        super().__init__("Command '{}' not Found!".format(name))


class CCommandAlreadyExists(CCException):
    def __init__(self, name: str = "Unknown"):
        super().__init__("A command/alias called `{}` already exists!".format(name))


class CCommandNotInGuild(CCException):
    def __init__(self, name: str = "Unknown"):
        super().__init__("Custom command only available in guilds")


class CCommandNoPerm(CCException):
    def __init__(self, name: str = "Unknown"):
        super().__init__("You have no permissions to use this command")


class CCommandDisabled(CCException):
    def __init__(self, name: str = "Unknown"):
        super().__init__("This command is disabled")


class MissingMuteRole(Exception):
    def __init__(self, ctx):
        super().__init__(
            "This guild doesn't have mute role set yet!\n"
            + "Use `{0}mute create Muted` or `{0}mute set @Muted` to setup mute role.".format(
                ctx.clean_prefix
            )
        )
