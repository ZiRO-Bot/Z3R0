from ..interface import Block
from ..interpreter import Context
from .helpers import helper_parse_if


class SilentBlock(Block):
    """
    Don't send command block's output
    """

    def will_accept(self, ctx: Context):
        dec = ctx.verb.declaration.lower()
        return any([dec == "silent", dec == "silence"])

    def process(self, ctx: Context):
        if "silent" in ctx.response.actions.keys():
            return None
        if ctx.verb.parameter is None:
            value = True
        else:
            value = helper_parse_if(ctx.verb.parameter)
        ctx.response.actions["silent"] = value
        return ""
