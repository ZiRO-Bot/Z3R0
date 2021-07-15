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
from exts.utils.other import ArgumentParser, UserFriendlyBoolean

# Also includes aliases
ROLE_TYPES = {
    "moderator": "modRole",
    "mod": "modRole",
    "mute": "mutedRole",
    "muted": "mutedRole",
    "regular": "",
}


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
        parser.add_argument("--channel", aliases=("--ch",))
        parser.add_argument("--raw", "-r", action=UserFriendlyBoolean)
        parser.add_argument("--disable", "-d", action=UserFriendlyBoolean)
        parser.add_argument("message", nargs="*")

        parsed, _ = parser.parse_known_from_string(arguments)

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

        if disable is True:
            await self.bot.setGuildConfig(ctx.guild.id, f"{type}Ch", None)
            e.add_field(name="Status", value="`Disabled`")
            return await ctx.try_reply(embed=e)

        if raw is True:
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
        aliases=("wel",),
        brief="Set welcome message and/or channel",
        description="Set welcome message and/or channel\n`TagScript` is supported!",
        usage="[message] [options]",
        extras=dict(
            example=(
                "welcome Welcome to {guild}, {user(name)}! ch: #userlog",
                "welcome Hello, {user(name)} 👋",
                "welcome raw: on",
                "welcome disable: true",
            ),
            flags={
                ("channel", "ch"): "Set welcome channel",
                "raw": (
                    "Send welcome's raw message (Useful for editing"
                    ", will prevent you from setting welcome message/channel)"
                ),
                "disable": "Disable welcome event",
            },
        ),
    )
    async def welcome(self, ctx, *, arguments):
        await self.handleGreetingConfig(ctx, arguments, type="welcome")

    @commands.command(
        aliases=("fw",),
        brief="Set farewell message and/or channel",
        description="Set farewell message and/or channel\n`TagScript` is supported!",
        usage="[message] [options]",
        extras=dict(
            example=(
                "farewell Bye ch: #userlog",
                "farewell Goodbye, {user(name)}!",
                "farewell raw: on",
                "farewell disable: true",
            ),
            flags={
                ("channel", "ch"): "Set farewell channel",
                "raw": (
                    "Send farewell's raw message (Useful for editing"
                    ", will prevent you from setting farewell message/channel)"
                ),
                "disable": "Disable farewell event",
            },
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
        aliases=("ml",),
        brief="Set modlog channel",
        description=(
            "Set modlog channel\n\n__**Options:**__\n`--disable` | `-d`: "
            "Disable modlog"
        ),
        usage="[channel] [options]",
        extras=dict(example=("modlog #modlog", "modlog -d", "ml --disable")),
    )
    async def modlog(self, ctx, *, arguments):
        await self.handleLogConfig(ctx, arguments, "modlog")

    @commands.command(
        aliases=("purge", "userlog"),
        brief="Set purgatory channel",
        description=(
            "Set purgatory channel\n\n__**Options:**__\n`--disable` | `-d`: "
            "Disable purgatory"
        ),
        usage="[channel] [options]",
        extras=dict(example=("purgatory #userlog", "purge -d", "userlog --disable")),
    )
    async def purgatory(self, ctx, *, arguments):
        await self.handleLogConfig(ctx, arguments, "purgatory")

    @commands.group(name="role", brief="Manage guild's role")
    @checks.is_admin()
    async def _role(self, ctx):
        # Role manager
        pass

    async def setMutedPerms(self, ctx, role: discord.Role):
        """Just loop through channels and overwriting muted role's perm"""
        for channel in ctx.guild.channels:
            perms: discord.PermissionOverwrite = channel.overwrites_for(role)

            perms.update(
                # speak=False,
                send_messages=False,
            )

            await channel.set_permissions(
                target=role,
                overwrite=perms,
                reason="Mute role set to {} by {}".format(role.name, ctx.author),
            )

    @_role.command(
        name="create",
        aliases=("+", "make"),
        brief="Create new role",
        usage="(name) [-t type]",
    )
    async def roleMake(self, ctx, *, arguments):
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--type", "-t")
        parser.add_argument("name", nargs="+")

        parsed, _ = parser.parse_known_args(shlex.split(arguments))

        name = " ".join(parsed.name)
        type = parsed.type or "regular"

        if (type := type.lower()) in ROLE_TYPES:
            msg = await ctx.try_reply(
                embed=ZEmbed.loading(),
            )

            role = await ctx.guild.create_role(name=name)

            if not role:
                # TODO: Maybe return a message to tell user that the command fail
                return

            if type != "regular":
                await self.setGuildRole(ctx.guild.id, ROLE_TYPES[type], role.id)

                if any([type == "mute", type == "muted"]):
                    await self.setMutedPerms(ctx, role)

            e = ZEmbed.success(
                title="SUCCESS: Role has been created",
                description="**Name**: {}\n**Type**: `{}`\n**ID**: `{}`".format(
                    role.name, type, role.id
                ),
            )
            return await msg.edit(embed=e)

        return await ctx.error(
            "Available role type: {}".format(
                ", ".join([f"`{type}`" for type in ROLE_TYPES])
            ),
            title="Invalid role type!",
        )

    @_role.command(
        name="set",
        aliases=("&",),
        brief="Turn regular role into special role",
        usage="(name) (-t type)",
    )
    async def roleSet(self, ctx, *, arguments):
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--type", "-t", required=True)
        parser.add_argument("role", nargs="+")

        parsed, _ = parser.parse_known_args(shlex.split(arguments))

        roleArg = " ".join(parsed.role)
        type = parsed.type

        disallowed = ("regular",)

        if (type := type.lower()) in ROLE_TYPES and type not in disallowed:
            msg = await ctx.try_reply(
                embed=ZEmbed.loading(),
            )

            role = await commands.RoleConverter().convert(ctx, roleArg)

            if not role:
                return

            if type != "regular":
                await self.setGuildRole(ctx.guild.id, ROLE_TYPES[type], role.id)

                if any([type == "mute", type == "muted"]):
                    await self.setMutedPerms(ctx, role)

            e = ZEmbed.success(
                title="SUCCESS: Role has been modified",
                description="**Name**: {}\n**Type**: `{}`\n**ID**: `{}`".format(
                    role.name, type, role.id
                ),
            )
            return await msg.edit(embed=e)

        return await ctx.error(
            "Available role type: {}".format(
                ", ".join(
                    [f"`{type}`" for type in ROLE_TYPES if type not in disallowed]
                )
            ),
            title="Invalid role type!",
        )


def setup(bot):
    bot.add_cog(Admin(bot))
