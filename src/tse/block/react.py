from ..interface import Block
from ..interpreter import Context


class ReactBlockBase(Block):
    """
    Base Block for React Block
    """

    def __init__(self, type: str):
        super().__init__()
        self.type = type

    def will_accept(self, ctx: Context):
        dec = ctx.verb.declaration.lower()
        return dec == self.type

    def process(self, ctx: Context):
        if not ctx.verb.payload:
            return None
        ctx.response.actions[self.type] = [emoji.strip() for emoji in ctx.verb.payload.split(" ") if emoji]
        return ""


class ReactBlock(ReactBlockBase):
    """
    React the custom command's output. Up to 5 emojis.

    Should support both unicode and custom emojis.

    Separated by spaces.

    Example
    -------
    >>> {react: <:verified:747802457798869084> 🤔}
    """

    def __init__(self):
        super().__init__("react")


class ReactUBlock(ReactBlockBase):
    """
    React the custom command invokation message. Up to 5 emojis.

    Should support both unicode and custom emojis.

    Separated by spaces.

    Example
    -------
    >>> {reactu: <:verified:747802457798869084> 🤔}
    """

    def __init__(self):
        super().__init__("reactu")
