"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import random
from typing import Optional

from TagScriptEngine import Block, Context, helper_parse_if


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

    def process(self, ctx: Context) -> Optional[str]:
        if ctx.verb.payload is None:
            return None

        spl = []
        if "~" in ctx.verb.payload:
            spl = ctx.verb.payload.split("~")
        else:
            spl = ctx.verb.payload.split(",")

        # tmp, spl = spl, []
        values = []
        weights = []
        for i in spl:
            try:
                weight, res = i.split("|")
                weight = int(weight)
            except ValueError:
                weight = 1
                try:
                    res: str = res
                except NameError:
                    res: str = i

            values.append(str(res))
            weights.append(weight)
            del res

        if ctx.verb.parameter:
            random.seed(ctx.verb.parameter)

        return random.choices(values, weights=weights)[0]
