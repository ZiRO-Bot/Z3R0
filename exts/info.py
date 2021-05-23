"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import discord
import time


from .utils.infoQuote import *
from discord.ext import commands


# TODO: Move this somewhere in `exts/utils/` folder
async def authorOrReferenced(ctx):
    if ref := ctx.message.reference:
        # Get referenced message author
        # if user reply to a message while doing this command
        return (
            ref.cached_message.author
            if ref.cached_message
            else (await ctx.fetch_message(ref.message_id)).author
        )
    return ctx.author


class Info(commands.Cog):
    """Commands that gives you information."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["p"])
    async def ping(self, ctx):
        """Tell the ping of the bot to the discord servers."""
        start = time.perf_counter()
        e = discord.Embed(
            title="Pong!",
            timestamp=ctx.message.created_at,
            colour=self.bot.colour,
        )
        e.add_field(
            name="<a:loading:776255339716673566> | Websocket",
            value=f"{round(self.bot.latency*1000)}ms",
        )
        e.set_footer(text="Requested by {}".format(str(ctx.author)))
        msg = await ctx.send(embed=e)
        end = time.perf_counter()
        msg_ping = (end - start) * 1000
        e.add_field(
            name="<a:typing:785053882664878100> | Typing",
            value=f"{round(msg_ping)}ms",
            inline=False,
        )
        await msg.edit(embed=e)

    @commands.command(aliases=["av", "userpfp", "pfp"])
    async def avatar(self, ctx, user: discord.User = None):
        """Show member's avatar image."""
        if not user:
            user = await authorOrReferenced(ctx)

        # Embed stuff
        e = discord.Embed(
            title="{}'s Avatar".format(user.name),
            colour=self.bot.colour,
            description="[`JPEG`]({})".format(user.avatar_url_as(format="jpg"))
            + " | [`PNG`]({})".format(user.avatar_url_as(format="png"))
            + " | [`WEBP`]({})".format(user.avatar_url_as(format="webp"))
            + (
                " | [`GIF`]({})".format(user.avatar_url_as(format="gif"))
                if user.is_avatar_animated()
                else ""
            ),
            timestamp=ctx.message.created_at,
        )
        e.set_image(url=user.avatar_url_as(size=1024))
        e.set_footer(
            text="Requested by {}".format(str(ctx.author)),
            icon_url=ctx.author.avatar_url,
        )
        await ctx.reply(embed=e, mention_author=False)


def setup(bot):
    bot.add_cog(Info(bot))
