"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import datetime as dt
import discord


from core.mixin import CogMixin
from discord.ext import commands


def formatDateTime(datetime):
    return datetime.strftime("%A, %d %b %Y • %H:%M:%S UTC")


class Timer(commands.Cog, CogMixin):
    """Time-related commands."""

    @commands.command()
    async def time(self, ctx):
        """Get current time."""
        # TODO: Add timezone
        e = discord.Embed(
            title="Current Time",
            description=formatDateTime(dt.datetime.utcnow()),
            colour=self.bot.colour,
        )
        await ctx.try_reply(embed=e)


def setup(bot):
    bot.add_cog(Timer(bot))
