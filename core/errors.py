class BotException(Exception):
    pass


class CCException(BotException):
    pass


class CCommandNotFound(CCException):
    def __init__(self, name: str = "Unknown"):
        super().__init__("Command '{}' not Found!".format(name))


class CCommandAlreadyExists(CCException):
    def __init__(self, name: str = "Unknown"):
        super().__init__("A command/alias called `{}` already exists!".format(name))
