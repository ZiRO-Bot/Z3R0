from TagScriptEngine import Verb, Interpreter, block
from TagScriptEngine.interface import Adapter
from typing import Optional


class StringParamAdapter(Adapter):
    def __init__(self, string: str, params=Optional[dict]):
        self.string: str = string
        self.params = params

    def get_value(self, ctx: Verb):
        if not ctx.parameter:
            return self.string
        try:
            if ctx.parameter in list(self.params.keys()):
                return self.params[ctx.parameter]
        except:
            return self.string
