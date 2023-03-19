"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import sys
from contextlib import suppress
from typing import TYPE_CHECKING, Optional

import discord
import pytz
from discord.app_commands import locale_str as _
from discord.ext import commands

from ...core import commands as cmds
from ...core import db
from ...core.converter import TimeAndArgument
from ...core.mixin import CogMixin
from ...utils.format import formatDateTime, formatDiscordDT
from ...utils.other import utcnow
from ._views import LinkView


if TYPE_CHECKING:
    from ...core.bot import ziBot


class TimerData:
    __slots__ = (
        "id",
        "event",
        "args",
        "kwargs",
        "extra",
        "expires",
        "createdAt",
        "owner",
    )

    def __init__(self, data: dict):
        self.id = data["id"]
        self.event = data["event"]
        self.args: list = []
        self.kwargs: dict = {}
        try:
            self.extra = data["extra"]
            self.args = self.extra.pop("args", [])
            self.kwargs = self.extra.pop("kwargs", {})
        except TypeError:
            self.extra = data["extra"]
        self.expires = data["expires"]
        self.createdAt = data["created"]
        self.owner = data["owner"]

    @classmethod
    def temporary(cls, expires, created, event, owner, args, kwargs):
        return cls(
            {
                "id": None,
                "event": event,
                "extra": {"args": args, "kwargs": kwargs},
                "expires": expires,
                "created": created,
                "owner": owner,
            }
        )


# TODO: Slash
class Timer(commands.Cog, CogMixin):
    """Time-related commands."""

    icon = "🕑"
    cc = True

    def __init__(self, bot: ziBot) -> None:
        super().__init__(bot)

        pyVer = sys.version_info
        if pyVer[1] >= 10:
            self.haveData = asyncio.Event()
        else:
            self.haveData = asyncio.Event(loop=bot.loop)
        self._currentTimer: Optional[TimerData] = None

    async def cog_load(self) -> None:
        self.task = self.bot.loop.create_task(self.dispatchTimers())

    def cog_unload(self) -> None:
        task = getattr(self, "task", None)
        if task:
            task.cancel()

    def restartTimer(self) -> None:
        self.task.cancel()
        self.task = self.bot.loop.create_task(self.dispatchTimers())

    async def getActiveTimer(self, days: int = 7) -> Optional[TimerData]:
        data = await db.Timer.filter(expires__lt=utcnow() + dt.timedelta(days=days)).order_by("expires").values()  # type: ignore
        return TimerData(data[0]) if data else None

    async def waitForActiveTimer(self, days: int = 7) -> Optional[TimerData]:
        timer: Optional[TimerData] = await self.getActiveTimer(days=days)
        if timer is not None:
            self.haveData.set()
            return timer

        self.haveData.clear()
        self._currentTimer: Optional[TimerData] = None
        await self.haveData.wait()
        return await self.getActiveTimer(days=days)

    async def callTimer(self, timer: TimerData) -> None:
        # delete the timer
        await db.Timer.filter(id=timer.id).delete()

        # dispatch the event
        eventName = f"{timer.event}_timer_complete"
        self.bot.dispatch(eventName, timer)

    async def dispatchTimers(self) -> None:
        try:
            while not self.bot.is_closed():
                timer = self._currentTimer = await self.waitForActiveTimer(days=40)
                now = utcnow()

                if timer.expires >= now:  # type: ignore # Already waited for active timer
                    sleepAmount = (timer.expires - now).total_seconds()  # type: ignore
                    await asyncio.sleep(sleepAmount)

                await self.callTimer(timer)  # type: ignore
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed):
            self.restartTimer()

    async def createTimer(self, *args, **kwargs) -> TimerData:
        when, event, *args = args

        now = kwargs.pop("created", utcnow())
        owner = kwargs.pop("owner", None)

        whenTs = when
        nowTs = now

        timer: TimerData = TimerData.temporary(
            event=event,
            args=args,
            kwargs=kwargs,
            expires=whenTs,
            created=nowTs,
            owner=owner,
        )
        delta = (when - now).total_seconds()

        values = {
            "event": event,
            "extra": {"args": args, "kwargs": kwargs},
            "expires": whenTs,
            "created": nowTs,
            "owner": owner,
        }
        _dbTimer = await db.Timer.create(**values)
        timer.id = _dbTimer.id

        if delta <= (86400 * 40):  # 40 days
            self.haveData.set()

        if self._currentTimer and when < self._currentTimer.expires:
            # cancel the task and re-run it
            self.restartTimer()

        return timer

    @commands.command(
        aliases=["timer", "remind"],
        description="Reminds you about something after certain amount of time",
    )
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def reminder(self, ctx, *, argument: TimeAndArgument) -> discord.Message:
        now = utcnow()
        when = argument.when
        message = argument.arg or "Reminder"
        if not when:
            return await ctx.try_reply("Invalid time.")

        await self.createTimer(
            when,
            "reminder",
            ctx.channel.id,
            message,
            messageId=ctx.message.id,
            created=now,
            owner=ctx.author.id,
        )

        return await ctx.try_reply(
            "In {}, {}".format(
                argument.delta,
                message,
            )
        )

    @cmds.command(name=_("time"), description=_("time-desc"), hybrid=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def time(self, ctx, timezone: str = None) -> None:
        tz = None
        if timezone:
            with suppress(pytz.UnknownTimeZoneError):
                tz = pytz.timezone(timezone)

        dt = utcnow()
        if tz:
            dt = dt.astimezone(tz)

        # TODO: Add timezone
        e = discord.Embed(
            title="Current Time",
            description=formatDateTime(dt),
            colour=self.bot.colour,
        )
        e.set_footer(text="Timezone coming soon\u2122!")
        await ctx.try_reply(embed=e)

    @commands.Cog.listener("on_reminder_timer_complete")
    async def onReminderTimerComplete(self, timer: TimerData) -> None:
        channelId, message = timer.args
        authorId = timer.owner

        try:
            channel = self.bot.get_channel(channelId) or (await self.bot.fetch_channel(channelId))
        except discord.HTTPException:
            return

        guildId = channel.guild.id if isinstance(channel, discord.TextChannel) else "@me"
        messageId = timer.kwargs.get("messageId")
        msgUrl = f"https://discord.com/channels/{guildId}/{channelId}/{messageId}"

        await channel.send(  # type: ignore
            "<@{}>, {}: {}".format(
                authorId,
                formatDiscordDT(timer.createdAt, "R"),
                discord.utils.escape_mentions(message),
            ),
            view=LinkView(links=[("Jump to Source", msgUrl)]),
        )
