import datetime as dt
import re
from contextlib import suppress
from typing import Optional, Union

import discord
from dateutil.relativedelta import relativedelta
from discord.ext import commands
from humanize import naturaldelta

from ..utils.other import utcnow
from .context import Context
from .errors import DefaultError, HierarchyError


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
        self.when: Optional[dt.datetime] = None
        self.delta: Optional[str] = None

        match = TIME_REGEX.match(argument)
        if match:
            kwargs = {k: int(v) for k, v in match.groupdict().items() if v}
            if kwargs:
                self.arg = argument[match.end() :].strip()
                now = utcnow()
                try:
                    self.when = now + relativedelta(**kwargs)
                    self.delta = naturaldelta(self.when, when=now)
                except (ValueError, OverflowError):
                    raise DefaultError("Invalid time provided")
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
                raise commands.BadArgument("This member has not been banned before.") from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument("This member has not been banned before.")
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


def checkHierarchy(ctx, user, action: str = None) -> Optional[str]:
    """Check hierarchy stuff"""
    errMsg: Optional[str] = None

    if user.id == ctx.bot.user.id:
        errMsg = "Nice try."
    elif user == ctx.guild.owner:
        errMsg = "You can't {} guild owner!".format(action or "do this action to")
    else:
        # compare author and bot's top role vs target's top role
        with suppress(AttributeError):
            if ctx.me.top_role <= user.top_role:
                errMsg = "{}'s top role is higher or equals " "to **mine** in the hierarchy!".format(user)

        with suppress(AttributeError):
            if ctx.author != ctx.guild.owner and ctx.author.top_role <= user.top_role:  # guild owner doesn't need this check
                errMsg = "{}'s top role is higher or equals " "to **yours** in the hierarchy!".format(user)
    return errMsg


class Hierarchy(commands.Converter):
    def __init__(self, converter: commands.Converter = MemberOrUser, *, action: Optional[str] = None):
        self.converter: commands.Converter = converter()  # type: ignore
        self.action: str = action or "do that to"

    async def convert(self, ctx, arguments):
        converted: Union[discord.Member, discord.User] = await self.converter.convert(ctx, arguments)

        try:
            errMsg: Optional[str] = checkHierarchy(ctx, converted, self.action)
        except AttributeError:
            errMsg = "Invalid User/Member"

        # errMsg will always None unless check fails
        if errMsg is None:
            return converted

        raise HierarchyError(errMsg)
