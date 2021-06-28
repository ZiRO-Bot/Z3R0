"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import argparse
import discord
import shlex


from core.mixin import CogMixin
from discord.ext import commands
from exts.utils.format import ZEmbed


class Admin(commands.Cog, CogMixin):
    """Admin-only commands to configure the bot."""

    icon = "\u2699"

    @commands.command(
        aliases=["fw"],
        brief="Set farewell message and/or channel",
        description=(
            "Set farewell message and/or channel\n`TagScript` is "
            "supported!\n\n__**Options:**__\n`--channel` | `-c`: Set farewell "
            "channel\n`--raw` | `-r`: Send farewell's raw message (Useful for "
            "editing, will prevent you from setting farewell message/channel)"
        ),
        usage="[message] [-c #channel] [-r]",
        example=(
            "farewell Bye -c #userlog",
            "farewell Goodbye, {user(name)}!",
            "farewell -r"
        )
    )
    async def farewell(self, ctx, *, arguments):
        if not arguments:
            # Nothing to do here.
            return

        # Parsing arguments
        parser = argparse.ArgumentParser(allow_abbrev=False, add_help=False)
        parser.add_argument("--channel", "-c")
        parser.add_argument("--raw", "-r", action="store_true")
        parser.add_argument("message", nargs="*")

        parsed, _ = parser.parse_known_args(shlex.split(arguments))

        raw = parsed.raw

        changeMsg = False
        if not raw and parsed.message:
            changeMsg = True
            message = " ".join(parsed.message)

        channel = None
        if not raw and parsed.channel:
            channel = await commands.TextChannelConverter().convert(ctx, parsed.channel)

        e = ZEmbed(
            title="Farewell config has been updated",
        )

        if raw:
            message = await self.bot.getGuildConfig(ctx.guild.id, "farewellMsg")
            return await ctx.try_reply(discord.utils.escape_markdown(message))

        if changeMsg:
            await self.bot.setGuildConfig(ctx.guild.id, "farewellMsg", message)
            e.add_field(name="Message", value=message, inline=False)
        if channel is not None:
            await self.bot.setGuildConfig(ctx.guild.id, "farewellCh", channel.id)
            e.add_field(name="Channel", value=channel.mention)

        return await ctx.try_reply(embed=e)


def setup(bot):
    bot.add_cog(Admin(bot))
