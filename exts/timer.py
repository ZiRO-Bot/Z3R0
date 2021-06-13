"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import datetime as dt
import discord


from core.mixin import CogMixin
from discord.ext import commands
from exts.utils import dbQuery


def formatDateTime(datetime):
    return datetime.strftime("%A, %d %b %Y • %H:%M:%S UTC")


class Timer(commands.Cog, CogMixin):
    """Time-related commands."""

    icon = "🕑"

    def __init__(self, bot):
        super().__init__(bot)

        self.currentTimer = None
        self.task = None
        self.bot.loop.create_task(self.asyncInit())

    async def asyncInit(self):
        async with self.bot.db.transaction():
            await self.bot.db.execute(dbQuery.createTimerTable)

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


def setup(bot):
    bot.add_cog(Timer(bot))
