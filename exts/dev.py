"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import discord


from core.mixin import CogMixin
from exts.utils import infoQuote
from discord.ext import commands


class Developer(commands.Cog, CogMixin):
    """Debugging tools for bot devs."""

    async def cog_check(self, ctx):
        """Only bot master able to use debug cogs."""
        return (
            (self.bot.master
            and ctx.author.id in self.bot.master)
            or commands.is_owner().predicate(ctx)
        )

    def notMe():
        async def pred(ctx):
            return not (
                (ctx.bot.master
                and ctx.author.id in ctx.bot.master)
                or commands.is_owner().predicate(ctx)
            )

        return commands.check(pred)


    @commands.group(invoke_without_command=True)
    async def test(self, ctx, text):
        """Test something."""
        await ctx.send(infoQuote.info("Test") + " {}".format(text))

    @test.command()
    async def error(self, ctx):
        """Test error handler."""
        raise RuntimeError("Haha error brrr")

    @test.command()
    @notMe()
    async def noperm(self, ctx):
        """Test no permission."""
        pass


def setup(bot):
    bot.add_cog(Developer(bot))
