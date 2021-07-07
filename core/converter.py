import datetime as dt
import re


from core.context import Context
from dateutil.relativedelta import relativedelta
from discord.ext import commands
from exts.utils.other import utcnow
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
        # Default values
        self.arg = argument
        self.when = None
        self.delta = None

        match = TIME_REGEX.match(argument)
        if match:
            kwargs = {k: int(v) for k, v in match.groupdict().items() if v}
            if kwargs:
                self.arg = argument[match.end() :].strip()
                now = utcnow()
                self.when = now + relativedelta(**kwargs)
                self.delta = naturaldelta(self.when, when=now)
                return self
            # prevent NaN (empty) time like 'min' makes arg empty
            self.arg = argument

        # TODO: Try to parse "specific time" (8:00am or 16 Jun 2021)
        return self
