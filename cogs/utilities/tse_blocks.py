from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.interface import Block
from typing import Optional
import random

class RandomBlock(Block):
    def will_accept(self, ctx : Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return any([dec == "random", dec == "#", dec =="rand"])

    def weighted_random(self, pairs, seed = None):
        total = sum(pair[0] for pair in pairs)
        if seed:
            random.seed(seed)
        r = random.randint(1, total)
        for (weight, value) in pairs:
            r -= weight
            if r <= 0: return value

    def process(self, ctx : Interpreter.Context) -> Optional[str]:
        if ctx.verb.payload is None:
            return None
        spl = []
        if "~" in ctx.verb.payload:
            spl = ctx.verb.payload.split("~")
        else:
            spl = ctx.verb.payload.split(",")
        
        tmp, spl = spl, []
        for i in tmp:
            pre = i.split("|")
        
            # Convert weight to int if possible
            try:
                pre[0] = int(pre[0])
                if pre[0] < 0:
                    pre[0] = None
            except ValueError:
                if len(pre) > 1:
                    pre[0] = None
            
            if len(pre) > 1 and isinstance(pre[0], int):
                spl.append((pre[0], pre[1]))
            elif len(pre) > 1:
                spl.append((1, i))
            else:
                spl.append((1, pre[0]))

        random.seed(ctx.verb.parameter)

        result = self.weighted_random(spl, ctx.verb.parameter)
        return result
