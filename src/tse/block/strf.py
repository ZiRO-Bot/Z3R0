import datetime as dt
from typing import Optional

from ..interface import Block
from ..interpreter import Context


class StrfBlock(Block):
    def will_accept(self, ctx: Context) -> bool:
        return ctx.verb.declaration == "strf"

    def process(self, ctx: Context) -> Optional[str]:
        if not ctx.verb.payload:
            return

        if ctx.verb.parameter:
            if ctx.verb.parameter.isdigit():
                try:
                    t = dt.datetime.fromtimestamp(int(ctx.verb.parameter))
                except Exception:
                    return
            else:
                try:
                    t = dt.datetime.strptime(ctx.verb.parameter, "%Y-%m-%d %H.%M.%S")
                except ValueError:
                    return
        else:
            t = dt.datetime.now(tz=dt.timezone.utc)
        if not t.tzinfo:
            t.replace(tzinfo=dt.timezone.utc)
        return t.strftime(ctx.verb.payload)
