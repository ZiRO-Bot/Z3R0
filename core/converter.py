import datetime as dt
import discord
import re


from core.context import Context
from dateutil.relativedelta import relativedelta
from discord.ext import commands
from exts.utils.other import utcnow
from humanize import naturaldelta


TIME_REGEX = re.compile(
    r"""
        (?:(?P<years>([\d]+))(?:\ )?(?:years?|y))?
        (?:(?P<months>([\d]+))(?:\ )?(?:months?|mo))?
        (?:(?P<weeks>([\d]+))(?:\ )?(?:weeks?|w))?
        (?:(?P<days>([\d]+))(?:\ )?(?:days?|d))?
        (?:(?P<hours>([\d]+))(?:\ )?(?:hours?|h))?
        (?:(?P<minutes>([\d]+))(?:\ )?(?:minutes?|mins?|m))?
        (?:(?P<seconds>([\d]+))(?:\ )?(?:seconds?|secs?|s))?
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


# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/mod.py#L109-L123
class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument('This member has not been banned before.') from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument('This member has not been banned before.')
        return entity


class MemberOrUser(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.MemberConverter().convert(ctx, argument)
        except commands.MemberNotFound:
            try:
                return await commands.UserConverter().convert(ctx, argument)
            except commands.UserNotFound:
                return None
