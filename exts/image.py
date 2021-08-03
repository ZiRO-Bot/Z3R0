"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from io import BytesIO

import discord
from discord.ext import commands

from core.converter import MemberOrUser
from core.mixin import CogMixin


class Image(commands.Cog, CogMixin):
    """Image manipulation cog."""

    icon = "🖼️"

    def __init__(self, bot):
        super().__init__(bot)
        # Image manipulation are too heavy for my stuff apparently
        # so i host it on repl.it
        # Source: https://github.com/ZiRO-Bot/ImageManip
        self.imageManipUrl = "https://imagemanip.null2264.repl.co"

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def blurplify(self, ctx, memberOrUser: MemberOrUser = None):
        user: discord.User = memberOrUser or ctx.author
        userAv = user.avatar_url_as(format="png")
        async with self.bot.session.get(
            f"{self.imageManipUrl}/blurplify?url={userAv}"
        ) as req:
            if str(req.content_type).startswith("image/"):
                imgBytes = await req.read()
                img = discord.File(fp=BytesIO(imgBytes), filename="blurplified.png")
                await ctx.try_reply(file=img)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def triggered(self, ctx, memberOrUser: MemberOrUser = None):
        user: discord.User = memberOrUser or ctx.author
        userAv = user.avatar_url_as(format="png")
        async with self.bot.session.get(
            f"{self.imageManipUrl}/triggered?url={userAv}"
        ) as req:
            if str(req.content_type).startswith("image/"):
                imgBytes = await req.read()
                img = discord.File(fp=BytesIO(imgBytes), filename="triggered.gif")
                await ctx.try_reply(file=img)


def setup(bot):
    bot.add_cog(Image(bot))
