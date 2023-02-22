from ..interface import Adapter
from ..verb import Verb


class ArgumentAdapter(Adapter):
    def __init__(self, arguments: str):
        self.arguments: str = arguments

    def __repr__(self):
        return f"<{type(self).__qualname__} arguments={repr(self.arguments)}>"

    def get_value(self, ctx: Verb) -> str:
        if not ctx.parameter:
            return self.arguments

        try:
            return self.arguments.split(" ")[int(ctx.parameter)]
        except:
            return self.arguments
