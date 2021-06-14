import datetime as dt
import re


from core.context import Context
from dateutil.relativedelta import relativedelta
from discord.ext import commands
from humanize import naturaldelta


TIME_REGEX = re.compile(
    r"""
        (?:(?P<years>([\d]*))(?:\ )?(?:years?|y))?
        (?:(?P<months>([\d]*))(?:\ )?(?:months?|mo))?
        (?:(?P<weeks>([\d]*))(?:\ )?(?:weeks?|w))?
        (?:(?P<days>([\d]*))(?:\ )?(?:days?|d))?
        (?:(?P<hours>([\d]*))(?:\ )?(?:hours?|h))?
        (?:(?P<minutes>([\d]*))(?:\ )?(?:minutes?|mins?|m))?
        (?:(?P<seconds>([\d]*))(?:\ )?(?:seconds?|secs?|s))?
    """,
    re.VERBOSE | re.IGNORECASE,
)


class TimeAndArgument(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        match = TIME_REGEX.match(argument)
        if not match:
            return (None, argument, None)

        newArg = argument[match.end() :].strip()
        kwargs = {k: int(v) for k, v in match.groupdict().items() if v}
        now = dt.datetime.utcnow()
        when = now + relativedelta(**kwargs)
        delta = naturaldelta(when, when=now)
        return (when, newArg, delta)
