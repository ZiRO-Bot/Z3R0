"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import discord
import shlex


from core import checks
from core.mixin import CogMixin
from discord.ext import commands
from exts.utils import dbQuery
from exts.utils.format import ZEmbed
from exts.utils.other import ArgumentParser


class Admin(commands.Cog, CogMixin):
    """Admin-only commands to configure the bot."""

    icon = "\u2699"

    def __init__(self, bot):
        super().__init__(bot)

    async def getGuildRole(self, guildId: int, roleType: str):
        return await self.bot.getGuildConfig(guildId, roleType, "guildRoles")

    async def setGuildRole(self, guildId: int, roleType: str, roleId: int):
        return await self.bot.setGuildConfig(guildId, roleType, roleId, "guildRoles")

    async def cog_check(self, ctx):
        if not ctx.guild:
            # Configuration only for Guild
            return False

        # Check if member can manage_channels or have mod role
        return await checks.isMod(ctx)

    async def handleGreetingConfig(self, ctx, arguments, type: str):
        """Handle welcome and farewell configuration."""
        if not arguments:
            # Nothing to do here.
            return

        # Parsing arguments
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--channel", "-c")
        parser.add_argument("--raw", "-r", action="store_true")
        parser.add_argument("--disable", "-d", action="store_true")
        parser.add_argument("message", nargs="*")

        parsed, _ = parser.parse_known_args(shlex.split(arguments))

        disable = parsed.disable
        raw = parsed.raw

        changeMsg = False
        if not raw and not disable and parsed.message:
            changeMsg = True
            message = " ".join(parsed.message)

        channel = None
        if not raw and not disable and parsed.channel:
            channel = await commands.TextChannelConverter().convert(ctx, parsed.channel)

        e = ZEmbed(
            title=("Welcome" if type == "welcome" else "Farewell")
            + " config has been updated",
        )

        if disable:
            await self.bot.setGuildConfig(ctx.guild.id, f"{type}Ch", None)
            e.add_field(name="Status", value="`Disabled`")
            return await ctx.try_reply(embed=e)

        if raw:
            message = await self.bot.getGuildConfig(ctx.guild.id, f"{type}Msg")
            return await ctx.try_reply(discord.utils.escape_markdown(message))

        if changeMsg:
            await self.bot.setGuildConfig(ctx.guild.id, f"{type}Msg", message)
            e.add_field(name="Message", value=message, inline=False)
        if channel is not None:
            await self.bot.setGuildConfig(ctx.guild.id, f"{type}Ch", channel.id)
            e.add_field(name="Channel", value=channel.mention)

        return await ctx.try_reply(embed=e)

    @commands.command(
        aliases=["wel"],
        brief="Set welcome message and/or channel",
        description=(
            "Set welcome message and/or channel\n`TagScript` is "
            "supported!\n\n__**Options:**__\n`--channel` | `-c`: Set welcome "
            "channel\n`--raw` | `-r`: Send welcome's raw message (Useful for "
            "editing, will prevent you from setting welcome message/channel) "
            "\n`--disable` | `d`: Disable welcome event"
        ),
        usage="[message] [options]",
        example=(
            "welcome Welcome to {guild}, {user(name)}! -c #userlog",
            "welcome Hello, {user(name)} 👋",
            "welcome -r",
            "welcome --disable",
        ),
    )
    async def welcome(self, ctx, *, arguments):
        await self.handleGreetingConfig(ctx, arguments, type="welcome")

    @commands.command(
        aliases=["fw"],
        brief="Set farewell message and/or channel",
        description=(
            "Set farewell message and/or channel\n`TagScript` is "
            "supported!\n\n__**Options:**__\n`--channel` | `-c`: Set farewell "
            "channel\n`--raw` | `-r`: Send farewell's raw message (Useful for "
            "editing, will prevent you from setting farewell message/channel) "
            "\n`--disable` | `d`: Disable farewell event"
        ),
        usage="[message] [options]",
        example=(
            "farewell Bye -c #userlog",
            "farewell Goodbye, {user(name)}!",
            "farewell -r",
            "farewell --disable",
        ),
    )
    async def farewell(self, ctx, *, arguments):
        await self.handleGreetingConfig(ctx, arguments, type="farewell")

    async def handleLogConfig(self, ctx, arguments, type: str):
        """Handle configuration for logs (modlog, purgatory)"""
        # Parsing arguments
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--disable", "-d", action="store_true")
        parser.add_argument("channel", nargs="?", default="")

        parsed, _ = parser.parse_known_args(shlex.split(arguments))

        disable = parsed.disable

        e = ZEmbed(
            title=("Modlog" if type == "modlog" else "Purgatory")
            + " config has been updated"
        )

        if disable:
            await self.bot.setGuildConfig(ctx.guild.id, f"{type}Ch", None)
            e.add_field(name="Status", value="`Disabled`")
            return await ctx.try_reply(embed=e)

        if parsed.channel:
            channel = await commands.TextChannelConverter().convert(ctx, parsed.channel)
            await self.bot.setGuildConfig(ctx.guild.id, f"{type}Ch", channel.id)
            e.add_field(name="Channel", value=channel.mention)
            return await ctx.try_reply(embed=e)

    @commands.command(
        aliases=["ml"],
        brief="Set modlog channel",
        description=(
            "Set modlog channel\n\n__**Options:**__\n`--disable` | `-d`: "
            "Disable modlog"
        ),
        usage="[channel] [options]",
        example=("modlog #modlog", "modlog -d", "ml --disable"),
    )
    async def modlog(self, ctx, *, arguments):
        await self.handleLogConfig(ctx, arguments, "modlog")

    @commands.command(
        aliases=["purge", "userlog"],
        brief="Set purgatory channel",
        description=(
            "Set purgatory channel\n\n__**Options:**__\n`--disable` | `-d`: "
            "Disable purgatory"
        ),
        usage="[channel] [options]",
        example=("purgatory #userlog", "purge -d", "userlog --disable"),
    )
    async def purgatory(self, ctx, *, arguments):
        await self.handleLogConfig(ctx, arguments, "purgatory")

    @commands.group(name="role", brief="Manage guild's role")
    @checks.is_admin()
    async def _role(self, ctx):
        # Role manager
        pass

    @_role.command(
        name="create",
        aliases=["+", "make"],
        brief="Create new role",
        usage="(name) [-t type]",
    )
    async def roleMake(self, ctx, *, arguments):
        availableTypes = (
            "moderator",
            "mod",
            "mute",
            "muted",
            "regular",
        )

        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--type", "-t")
        parser.add_argument("name", nargs="+")

        parsed, _ = parser.parse_known_args(shlex.split(arguments))

        name = " ".join(parsed.name)
        type = parsed.type or "regular"

        if (type := type.lower()) in availableTypes:
            role = await ctx.guild.create_role(name=name)

            if any([type == "mute", type == "muted"]):
                await self.setGuildRole(ctx.guild.id, "mutedRole", role.id)
                for cat in ctx.guild.categories:
                    await cat.set_permissions(role, send_messages=False, speak=False)

            if any([type == "mod", type == "moderator"]):
                await self.setGuildRole(ctx.guild.id, "modRole", role.id)

            if role:
                return await ctx.try_reply(
                    "Role '{}' has been created".format(role.mention)
                )
            return

        return await ctx.try_reply(
            "Available role type: {}".format(
                ", ".join([f"`{type}`" for type in availableTypes])
            )
        )


def setup(bot):
    bot.add_cog(Admin(bot))
