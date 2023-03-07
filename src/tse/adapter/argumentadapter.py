import pyparsing as pp

from ..interface import Adapter
from ..verb import Verb


QUOTED_STRING = (pp.sglQuotedString() | pp.dblQuotedString()).setParseAction(pp.removeQuotes)
STRING = pp.Regex(r"\w+")
STRING_LIST = pp.OneOrMore(QUOTED_STRING | STRING)


class ArgumentAdapter(Adapter):
    """Handle user arguments

    Example:
        Block       : {args(0)}
        Input       : "test " test2 " test3 "
        Output      : ['test ', 'test2', ' test3 ']
        Block Output: test<SPACE> (or 'test ')
    """

    def __init__(self, arguments: str):
        self.arguments: str = arguments

    def __repr__(self):
        return f"<{type(self).__qualname__} arguments={repr(self.arguments)}>"

    def get_value(self, ctx: Verb) -> str:
        if not ctx.parameter:
            return self.arguments

        try:
            return STRING_LIST.parseString(self.arguments)[int(ctx.parameter)]
        except:
            return self.arguments
