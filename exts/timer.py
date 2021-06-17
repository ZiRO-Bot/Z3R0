"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import asyncio
import datetime as dt
import discord
import json


from core.converter import TimeAndArgument
from core.mixin import CogMixin
from discord.ext import commands
from exts.utils import dbQuery
from exts.utils.format import formatDateTime, ZEmbed


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

    def __init__(self, data):
        self.id = data[0]
        self.event = data[1]
        try:
            self.extra = json.loads(data[2])
            self.args = self.extra.pop("args", [])
            self.kwargs = self.extra.pop("kwargs", {})
        except TypeError:
            self.extra = data[2]
            self.args = None
            self.kwargs = None
        self.expires = dt.datetime.fromtimestamp(data[3])
        self.createdAt = dt.datetime.fromtimestamp(data[4])
        self.owner = data[5]

    @classmethod
    def temporary(cls, expires, created, event, owner, args, kwargs):
        return cls(
            [None, event, {"args": args, "kwargs": kwargs}, expires, created, owner]
        )


class Timer(commands.Cog, CogMixin):
    """Time-related commands."""

    icon = "🕑"

    def __init__(self, bot):
        super().__init__(bot)

        self.haveData = asyncio.Event(loop=bot.loop)
        self.currentTimer = None
        self.bot.loop.create_task(self.asyncInit())

    async def asyncInit(self):
        async with self.bot.db.transaction():
            await self.bot.db.execute(dbQuery.createTimerTable)
        self.task = self.bot.loop.create_task(self.dispatchTimers())

    async def getActiveTimer(self, days: int = 7):
        data = await self.bot.db.fetch_one(
            """
                SELECT * FROM timer
                WHERE
                    expires < :interval
                ORDER BY
                    expires ASC
            """,
            values={
                "interval": (dt.datetime.utcnow() + dt.timedelta(days=days)).timestamp()
            },
        )
        return TimerData(data) if data else None

    async def waitForActiveTimer(self, days: int = 7):
        timer = await self.getActiveTimer(days=days)
        if timer is not None:
            self.haveData.set()
            return timer

        self.haveData.clear()
        self.currentTimer = None
        await self.haveData.wait()
        return await self.getActiveTimer(days=days)

    async def callTimer(self, timer):
        # delete the timer
        async with self.bot.db.transaction():
            await self.bot.db.execute(
                "DELETE FROM timer WHERE timer.id=:id", values={"id": timer.id}
            )

        # dispatch the event
        eventName = f"{timer.event}_timer_complete"
        self.bot.dispatch(eventName, timer)

    async def dispatchTimers(self):
        try:
            while not self.bot.is_closed():
                timer = self.currentTimer = await self.waitForActiveTimer(days=40)
                now = dt.datetime.utcnow()

                if timer.expires >= now:
                    sleepAmount = (timer.expires - now).total_seconds()
                    await asyncio.sleep(sleepAmount)

                await self.callTimer(timer)
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed):
            self.task.cancel()
            self.task = self.bot.loop.create_task(self.dispatchTimers())

    async def createTimer(self, *args, **kwargs):
        when, event, *args = args

        now = kwargs.pop("created", dt.datetime.utcnow())
        owner = kwargs.pop("owner", None)

        whenTs = when.timestamp()
        nowTs = now.timestamp()

        timer: TimerData = TimerData.temporary(
            event=event,
            args=args,
            kwargs=kwargs,
            expires=whenTs,
            created=nowTs,
            owner=owner,
        )
        delta = (when - now).total_seconds()

        query = """
            INSERT INTO timer (event, extra, expires, created, owner)
            VALUES (:event, :extra, :expires, :created, :owner)
        """
        values = {
            "event": event,
            "extra": json.dumps({"args": args, "kwargs": kwargs}),
            "expires": whenTs,
            "created": nowTs,
            "owner": owner,
        }
        async with self.db.transaction():
            timer.id = await self.db.execute(query, values=values)

        if delta <= (86400 * 40):  # 40 days
            self.haveData.set()

        if self.currentTimer and when < self.currentTimer.expires:
            # cancel the task and re-run it
            self.task.cancel()
            self.task = self.bot.loop.create_task(self.dispatchTimers())

        return timer

    @commands.command(
        aliases=["timer", "remind"],
        brief="Reminds you about something after certain amount of time",
    )
    async def reminder(self, ctx, *, argument: TimeAndArgument):
        now = dt.datetime.utcnow()
        when = argument.when
        message = argument.arg or "Reminder"
        delta = argument.delta
        if not when:
            return await ctx.try_reply("Invalid time.")

        timer = await self.createTimer(
            when,
            "reminder",
            ctx.channel.id,
            message,
            messageId=ctx.message.id,
            created=now,
            owner=ctx.author.id,
        )
        return await ctx.send(
            "{} in {} ({})".format(
                message,
                delta,
                formatDateTime(when),
            )
        )

    @commands.command(brief="Get current time")
    async def time(self, ctx):
        # TODO: Add timezone
        e = discord.Embed(
            title="Current Time",
            description=formatDateTime(dt.datetime.utcnow()),
            colour=self.bot.colour,
        )
        e.set_footer(text="Timezone coming soon\u2122!")
        await ctx.try_reply(embed=e)

    @commands.Cog.listener()
    async def on_reminder_timer_complete(self, timer: TimerData):
        channelId, message = timer.args
        authorId = timer.owner

        try:
            channel = self.bot.get_channel(channelId) or (
                await self.bot.fetch_channel(channelId)
            )
        except discord.HTTPException:
            return

        guildId = (
            channel.guild.id if isinstance(channel, discord.TextChannel) else "@me"
        )
        messageId = timer.kwargs.get("messageId")
        msgUrl = f"https://discord.com/channels/{guildId}/{channelId}/{messageId}"

        e = ZEmbed(
            description="{} [`[?]`]({})".format(message, msgUrl),
        )

        await channel.send("<@{}>".format(authorId), embed=e)


def setup(bot):
    bot.add_cog(Timer(bot))
