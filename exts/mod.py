"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import discord
import humanize


from core.converter import TimeAndArgument
from core.mixin import CogMixin
from discord.ext import commands
from exts.utils.format import ZEmbed, formatDateTime


class Moderation(commands.Cog, CogMixin):
    """Moderation commands."""

    icon = "🛠️"

    @commands.command(usage="(user) [limit] [reason]")
    async def ban(self, ctx, user: discord.User, *, time: TimeAndArgument = None):
        defaultReason = "No reason."

        if user.id == ctx.bot.user.id:
            return await ctx.try_reply("Nice try.")

        if not self.bot.get_cog("Timer"):
            # Incase Timer cog not loaded yet.
            return await ctx.try_reply("Sorry, this command is current not available. Please try again later")

        try:
            reason = time.arg or defaultReason
            delta = time.delta
            time = time.when
        except AttributeError:
            reason = defaultReason

        desc = "**Reason**: {}".format(reason)
        if time is not None:
            desc += "\n**Duration**: {} ({})".format(delta, formatDateTime(time))
        e = ZEmbed.default(
            ctx,
            title="Banned {}".format(user),
            description=desc,
        )
        await ctx.send(embed=e)

def setup(bot):
    bot.add_cog(Moderation(bot))
