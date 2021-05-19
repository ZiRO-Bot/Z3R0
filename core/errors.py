class BotException(Exception):
    pass

class CCException(BotException):
    def __init__(self, name: str="Unknown"):
        super().__init__("Command '{}' not Found!".format(name))

class CCommandNotFound(CCException):
    pass


