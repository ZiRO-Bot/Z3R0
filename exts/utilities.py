"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import asyncio
import discord
import sys


from core.mixin import CogMixin
from decimal import Overflow, InvalidOperation
from discord.ext import commands
from exts.utils.format import ZEmbed
from exts.utils.other import NumericStringParser


class Utilities(commands.Cog, CogMixin):
    """Useful commands."""

    icon = "🔧"
    cc = True

    @commands.command(
        aliases=["calc", "c"],
        brief="Simple math evaluator",
        example=(
            "calc 12*6",
            "c 5^5",
            "math 50/2",
        ),
    )
    async def math(self, ctx, *, equation):
        try:
            result = NumericStringParser().eval(equation)
            if result > sys.maxsize:
                formattedResult = "HUGE NUMBER"
            else:
                formattedResult = "{0:,.1f}".format(result)
        except Overflow:
            formattedResult, result = ("Infinity",) * 2
        except InvalidOperation:
            formattedResult, result = ("ERR",) * 2
        except Exception as exc:
            return await ctx.send("I couldn't read that expression properly.")

        e = ZEmbed.default(
            ctx,
            fields=[
                ("Equation", discord.utils.escape_markdown(equation)),
                ("Result", formattedResult),
                ("Raw Result", result),
            ],
        )
        e.set_author(name="Simple Math Evaluator", icon_url=ctx.bot.user.avatar_url)
        return await ctx.try_reply(embed=e)


def setup(bot):
    bot.add_cog(Utilities(bot))
