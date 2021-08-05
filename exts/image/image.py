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
from utils.format import ZEmbed


class Image(commands.Cog, CogMixin):
    """Image manipulation cog."""

    icon = "🖼️"

    def __init__(self, bot):
        super().__init__(bot)
        # Image manipulation are too heavy for my stuff apparently
        # so i host it on repl.it
        # Source: https://github.com/ZiRO-Bot/ImageManip
        self.imageManipUrl = "https://imagemanip.null2264.repl.co"

    async def doImageFilter(
        self,
        ctx,
        _user: discord.User,
        type: str,
        format: str = "png",
    ) -> discord.Message:
        user: discord.User = _user or ctx.author
        userAv = user.avatar.with_format("png").url

        e = ZEmbed.loading()
        msg = await ctx.try_reply(embed=e)

        async with self.bot.session.get(
            f"{self.imageManipUrl}/{type}?url={userAv}"
        ) as req:
            if str(req.content_type).startswith("image/"):
                filename = f"{type}.{format}"
                imgBytes = await req.read()
                img = discord.File(fp=BytesIO(imgBytes), filename=filename)
                e = ZEmbed.default(ctx)
                e.set_image(url=f"attachment://{filename}")
                await msg.delete()
                return await ctx.try_reply(embed=e, file=img)
            else:
                await msg.delete()
                return await ctx.error("Unable to retrieve image")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def blurplify(self, ctx, memberOrUser: MemberOrUser = None):
        await self.doImageFilter(ctx, memberOrUser, "blurplify")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def triggered(self, ctx, memberOrUser: MemberOrUser = None):
        await self.doImageFilter(ctx, memberOrUser, "triggered", "gif")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def redify(self, ctx, memberOrUser: MemberOrUser = None):
        await self.doImageFilter(ctx, memberOrUser, "red")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def polaroid(self, ctx, memberOrUser: MemberOrUser = None):
        # Currently kinda broken
        await self.doImageFilter(ctx, memberOrUser, "polaroid")
