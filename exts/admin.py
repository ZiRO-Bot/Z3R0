"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import argparse
from typing import Optional, Union

import discord
from discord.ext import commands

from core import checks
from core.mixin import CogMixin
from exts.utils.format import ZEmbed
from exts.utils.other import ArgumentParser, UserFriendlyBoolean


# Also includes aliases
ROLE_TYPES = {
    "default": "autoRole",  # Role that automatically given upon joining a guild
    "member": "autoRole",
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
        parser.add_argument("message", action="extend", nargs="*")
        parser.add_argument("--message", action="extend", nargs="*")

        parsed, _ = await parser.parse_known_from_string(arguments)

        disable = parsed.disable
        raw = parsed.raw

        changeMsg = False
        message = None
        if not raw and not disable and parsed.message:
            changeMsg = True
            message = " ".join(parsed.message).strip()

        channel = None
        if not raw and not disable and parsed.channel:
            channel = await commands.TextChannelConverter().convert(ctx, parsed.channel)

        e = ZEmbed.success(
            title=("Welcome" if type == "welcome" else "Farewell")
            + " config has been updated",
        )

        if disable is True:
            await self.bot.setGuildConfig(
                ctx.guild.id, f"{type}Ch", None, "guildChannels"
            )
            e.add_field(name="Status", value="`Disabled`")
            return await ctx.try_reply(embed=e)

        if raw is True:
            message = await self.bot.getGuildConfig(ctx.guild.id, f"{type}Msg")
            return await ctx.try_reply(discord.utils.escape_markdown(message))

        if changeMsg and message:
            await self.bot.setGuildConfig(ctx.guild.id, f"{type}Msg", message)
            e.add_field(name="Message", value=message, inline=False)

        if channel is not None:
            await self.bot.setGuildConfig(
                ctx.guild.id, f"{type}Ch", channel.id, "guildChannels"
            )
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
                "message": "Append message text",
            },
            perms={
                "bot": "Manage Channels",
                "user": "Moderator Role or Manage Channels",
            },
        ),
    )
    @checks.mod_or_permissions(manage_channels=True)
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
                "message": "Append message text",
            },
            perms={
                "bot": "Manage Channels",
                "user": "Moderator Role or Manage Channels",
            },
        ),
    )
    @checks.mod_or_permissions(manage_channels=True)
    async def farewell(self, ctx, *, arguments):
        await self.handleGreetingConfig(ctx, arguments, type="farewell")

    async def handleLogConfig(self, ctx, arguments, type: str):
        """Handle configuration for logs (modlog, purgatory)"""
        # Parsing arguments
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--disable", action=UserFriendlyBoolean)
        parser.add_argument("channel", nargs="?", default=argparse.SUPPRESS)
        parser.add_argument("--channel", aliases=("--ch",))

        parsed, _ = await parser.parse_known_from_string(arguments)

        disable = parsed.disable

        e = ZEmbed.success(
            title=("Modlog" if type == "modlog" else "Purgatory")
            + " config has been updated"
        )

        if disable:
            await self.bot.setGuildConfig(
                ctx.guild.id, f"{type}Ch", None, "guildChannels"
            )
            e.add_field(name="Status", value="`Disabled`")
            return await ctx.try_reply(embed=e)

        if parsed.channel is not None:
            channel = await commands.TextChannelConverter().convert(ctx, parsed.channel)
            await self.bot.setGuildConfig(
                ctx.guild.id, f"{type}Ch", channel.id, "guildChannels"
            )
            e.add_field(name="Channel", value=channel.mention)
            return await ctx.try_reply(embed=e)

    @commands.command(
        aliases=("ml",),
        brief="Set modlog channel",
        description="Set modlog channel",
        usage="[channel] [options]",
        extras=dict(
            example=("modlog #modlog", "modlog ch: modlog", "ml disable: on"),
            flags={
                ("channel", "ch"): "Set modlog channel",
                "disable": "Disable modlog",
            },
            perms={
                "bot": "Manage Channels",
                "user": "Moderator Role or Manage Channels",
            },
        ),
    )
    @checks.mod_or_permissions(manage_channels=True)
    async def modlog(self, ctx, *, arguments):
        await self.handleLogConfig(ctx, arguments, "modlog")

    @commands.command(
        aliases=("purge", "userlog"),
        brief="Set purgatory channel",
        description="Set purgatory channel",
        usage="[channel] [options]",
        extras=dict(
            example=(
                "purgatory #userlog",
                "purge ch: userlog",
                "userlog disable: on",
            ),
            flags={
                ("channel", "ch"): "Set purgatory channel",
                "disable": "Disable purgatory",
            },
            perms={
                "bot": "Manage Channels",
                "user": "Moderator Role or Manage Channels",
            },
        ),
    )
    @checks.mod_or_permissions(manage_channels=True)
    async def purgatory(self, ctx, *, arguments):
        await self.handleLogConfig(ctx, arguments, "purgatory")

    @commands.group(
        name="role",
        brief="Manage guild's role",
        extras=dict(
            example=(
                "role set @Server Moderator type: moderator",
                "role + Muted type: muted",
                "role types",
            ),
            perms={
                "bot": "Manage Roles",
                "user": "Administrator",
            },
        ),
    )
    @checks.is_admin()
    async def _role(self, ctx):
        # Role manager
        pass

    async def updateMutedRoles(
        self,
        guild: discord.Guild,
        role: discord.Role,
        creator: Optional[discord.Member] = None,
    ) -> None:
        """Just loop through channels and overwriting muted role's perm"""
        for channel in guild.channels:
            perms: discord.PermissionOverwrite = channel.overwrites_for(role)

            perms.update(
                # speak=False,
                send_messages=False,
            )

            reason = "Mute role set to {}".format(role.name)
            if creator:
                reason += " by {}".format(creator)

            await channel.set_permissions(
                target=role,
                overwrite=perms,
                reason=reason,
            )

        # TODO: "Merge" old mute role with new mute role (adding new mute role to muted members)

    @_role.command(
        name="create",
        aliases=("+", "make"),
        brief="Create new role",
        usage="(role name) [type: role type]",
        extras=dict(
            perms={
                "bot": "Manage Roles",
                "user": "Administrator",
            },
        ),
    )
    async def roleMake(self, ctx, *, arguments):
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--type")
        parser.add_argument("name", action="extend", nargs="*")
        parser.add_argument("--name", action="extend", nargs="+")

        parsed, _ = await parser.parse_known_from_string(arguments)

        name = " ".join(parsed.name).strip()
        if not name:
            return await ctx.error("Name can't be empty!")

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
                    await self.updateMutedRoles(ctx.guild, role, ctx.author)

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
        usage="(role name) (type: role type)",
        extras=dict(
            perms={
                "bot": "Manage Roles",
                "user": "Administrator",
            },
        ),
    )
    async def roleSet(self, ctx, *, arguments):
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--type", "-t", required=True)
        parser.add_argument("role", action="extend", nargs="*")
        parser.add_argument("--role", action="extend", nargs="+")

        parsed, _ = await parser.parse_known_from_string(arguments)

        roleArg = " ".join(parsed.role).strip()
        if not roleArg:
            return await ctx.error("Role name can't be empty!")

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
                    await self.updateMutedRoles(ctx.guild, role, ctx.author)

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

    @_role.command(name="types", brief="Show all special role types")
    async def roleTypes(self, ctx):
        e = ZEmbed.minimal(
            title="Role Types",
            description="\n".join("- `{}`".format(role) for role in ROLE_TYPES),
        )
        e.set_footer(text="This list includes aliases (mod -> moderator)")
        return await ctx.try_reply(embed=e)

    @commands.command(
        brief="Set auto role",
        description=(
            "Set auto role.\n" "A role that will be given to a new member upon joining"
        ),
        usage="(role name)",
        extras=dict(
            example=("autorole @Member",),
            perms={
                "bot": "Manage Roles",
                "user": "Administrator",
            },
        ),
    )
    async def autorole(self, ctx, name: Union[discord.Role, str]):
        await ctx.try_invoke(
            self.roleMake if isinstance(name, str) else self.roleSet,
            arguments=f"{getattr(name, 'id', name)} type: member",
        )

    @commands.command(
        brief="Set announcement channel",
        extras=dict(
            example=("announcement #announcement",),
            perms={
                "bot": None,
                "user": "Manage Channels",
            },
        ),
    )
    async def announcement(self, ctx, channel: discord.TextChannel):
        await self.bot.setGuildConfig(
            ctx.guild.id, "announcementCh", channel.id, "guildChannels"
        )
        return await ctx.success(
            f"**Channel**: {channel.mention}",
            title="Announcement channel has been updated",
        )


def setup(bot):
    bot.add_cog(Admin(bot))
