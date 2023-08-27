"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import datetime as dt
import re
from contextlib import suppress
from typing import TYPE_CHECKING, Optional, Union

import discord
from dateutil.relativedelta import relativedelta
from discord.ext import commands
from humanize import naturaldelta

from ..utils import utcnow
from .context import Context
from .errors import DefaultError, HierarchyError


TIME_REGEX = re.compile(
    r"""
        (?:(?P<years>([\d]+))((?:\ )?years?|y))?
        (?:(?P<months>([\d]+))((?:\ )?months?|mo))?
        (?:(?P<weeks>([\d]+))((?:\ )?weeks?|w))?
        (?:(?P<days>([\d]+))((?:\ )?days?|d))?
        (?:(?P<hours>([\d]+))((?:\ )?hours?|h))?
        (?:(?P<minutes>([\d]+))((?:\ )?minutes?|(m(?:in(?:s)?)?)))?
        (?:(?P<seconds>([\d]+))((?:\ )?seconds?|(s(?:ec(?:s)?)?)))?
    """,
    re.VERBOSE | re.IGNORECASE,
)


class TimeAndArgument(commands.Converter):
    async def convert(self, _: Context, argument: str):
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
                    self.delta = naturaldelta(self.when - now)
                except (ValueError, OverflowError):
                    raise DefaultError("Invalid time provided")
                return self
            # prevent NaN (empty) time like 'min' makes arg empty
            self.arg = argument

        # TODO: Try to parse "specific time" (8:00am or 16 Jun 2021)
        return self


class BannedMember(commands.IDConverter):
    async def convert(self, ctx: Context, argument):
        try:
            memberId: int = await super().convert(ctx, argument)
            try:
                return await ctx.requireGuild().fetch_ban(discord.Object(id=memberId))
            except discord.NotFound:
                raise commands.BadArgument("This member has not been banned before.") from None
        except commands.ObjectNotFound:
            entity = [u async for u in ctx.requireGuild().bans(limit=None) if str(u.user) == argument]
            if len(entity) < 1:
                raise commands.BadArgument("This member has not been banned before.")
            return entity[0]


if TYPE_CHECKING:
    MemberOrUser = discord.User | discord.Member
else:

    class MemberOrUser(commands.Converter):
        async def convert(self, ctx: Context, argument):
            try:
                return await commands.MemberConverter().convert(ctx, argument)
            except commands.MemberNotFound:
                try:
                    return await commands.UserConverter().convert(ctx, argument)
                except commands.UserNotFound:
                    return None


def checkHierarchy(ctx: Context, user, action: str = None) -> Optional[str]:
    """Check hierarchy stuff"""
    guild = ctx.requireGuild()
    errMsg: Optional[str] = None

    botUser = ctx.bot.user
    if not botUser:
        raise DefaultError("Can't get bot user information")

    if user.id == botUser.id:
        errMsg = "Nice try."
    elif user == guild.owner:
        errMsg = "You can't {} guild owner!".format(action or "do this action to")
    else:
        # compare author and bot's top role vs target's top role
        with suppress(AttributeError):
            botMember: discord.Member = guild.get_member(botUser.id)
            if botMember.top_role <= user.top_role:
                errMsg = "{}'s top role is higher or equals " "to **mine** in the hierarchy!".format(user)

        with suppress(AttributeError):
            author: discord.Member = ctx.author  # type: ignore - Already handled
            if isinstance(author, discord.User):
                author = guild.get_member(author.id)

            if author != guild.owner and author.top_role <= user.top_role:  # guild owner doesn't need this check
                errMsg = "{}'s top role is higher or equals " "to **yours** in the hierarchy!".format(user)
    return errMsg


class Hierarchy(commands.Converter):
    def __init__(self, converter=MemberOrUser, *, action: Optional[str] = None):
        self.converter: commands.Converter = converter()  # type: ignore
        self.action: str = action or "do that to"

    async def convert(self, ctx: Context, arguments):
        converted: Union[discord.Member, discord.User] = await self.converter.convert(ctx, arguments)

        try:
            errMsg: Optional[str] = checkHierarchy(ctx, converted, self.action)
        except AttributeError:
            errMsg = "Invalid User/Member"

        # errMsg will always None unless check fails
        if errMsg is None:
            return converted

        raise HierarchyError(errMsg)


if TYPE_CHECKING:
    from typing_extensions import Annotated as ClampedRange  # type: ignore
else:

    class ClampedRange(commands.Range):
        """Similar to Range but instead of raising RangeError, it'll return the closest value to threshold"""

        async def convert(self, ctx: Context, value: str) -> int | float:
            try:
                converted = await super().convert(ctx, value)
            except commands.RangeError as e:
                count: int | float
                if self.annotation is str:
                    count = len(e.value)  # type: ignore
                else:
                    count = e.value  # type: ignore

                max_: int | float = e.maximum  # type: ignore
                min_: int | float = e.minimum  # type: ignore

                if count > max_:
                    return max_

                if count < min_:
                    return min_

                return count

            return converted
