import random


from TagScriptEngine import Block, Context, helper_parse_if
from typing import Tuple, Optional


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
        ctx.response.actions[self.type] = [
            emoji.strip() for emoji in ctx.verb.payload.split(" ") if emoji
        ]
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
    >>> {react: <:verified:747802457798869084> 🤔}
    """

    def __init__(self):
        super().__init__("reactu")

class RandomBlock(Block):
    """
    Example
    -------
    >>> {random:5|weighted~default}
    >>> {random:50~50}
    """
    def will_accept(self, ctx: Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return any([dec == "random", dec == "#", dec == "rand"])

    def weighted_random(self, pairs: Tuple[int, str], seed: str=None) -> Optional[str]:
        total = sum(pair[0] for pair in pairs)

        if seed:
            random.seed(seed)

        r = random.randint(1, total)
        for (weight, value) in pairs:
            r -= weight
            if r <= 0:
                return value

    def process(self, ctx: Context) -> Optional[str]:
        if ctx.verb.payload is None:
            return None

        spl = []
        if "~" in ctx.verb.payload:
            spl = ctx.verb.payload.split("~")
        else:
            spl = ctx.verb.payload.split(",")

        tmp, spl = spl, []
        for i in tmp:
            try:
                weight, res = i.split("|")
                weight = int(weight)
            except ValueError:
                weight = 1
                try:
                    res: str = res
                except NameError:
                    res: str = i

            spl.append((weight, str(res)))

            # pre = i.split("|")

            # # Convert weight to int if possible
            # try:
            #     pre[0] = int(pre[0])
            #     if pre[0] < 0 and len(pre) > 1:
            #         pre[0] = None
            # except ValueError:
            #     if len(pre) > 1:
            #         pre[0] = None

            # if len(pre) > 1 and isinstance(pre[0], int):
            #     spl.append((pre[0], str(pre[1])))
            # elif len(pre) > 1:
            #     spl.append((1, str(i)))
            # else:
            #     spl.append((1, str(pre[0])))

        # random.seed(ctx.verb.parameter)

        result = self.weighted_random(spl, ctx.verb.parameter)
        return result
