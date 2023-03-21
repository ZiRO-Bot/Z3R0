"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import Optional, Union

import discord
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands
from discord.utils import MISSING

from ...core import checks
from ...core import commands as cmds
from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.guild import GuildWrapper
from ...core.mixin import CogMixin
from ...utils.other import setGuildRole
from ._common import handleGreetingConfig
from ._flags import ROLE_TYPES, LogFlags, RoleCreateFlags, RoleSetFlags


class Admin(commands.Cog, CogMixin):
    """Collection of commands for admin/mods to configure the bot.

    Some commands may require `Administrator` permission.
    """

    icon = "\u2699"

    def __init__(self, bot) -> None:
        super().__init__(bot)

    async def cog_check(self, ctx):
        return ctx.guild is not None

    greetingGroup = app_commands.Group(name="greeting", description="...")

    welcomeDesc = _("welcome-desc")

    @greetingGroup.command(name=_("welcome"), description=welcomeDesc)
    @app_commands.describe(
        channel=_("welcome-arg-channel"),
        raw=_("welcome-arg-raw"),
        disable=_("welcome-arg-disable"),
        message=_("welcome-arg-message"),
    )
    @app_commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def welcomeSlash(
        self,
        interaction,
        message: str = None,
        channel: Optional[discord.TextChannel] = None,
        raw: bool = False,
        disable: bool = False,
    ):
        ctx = await Context.from_interaction(interaction)
        await handleGreetingConfig(ctx, "welcome", message=message, channel=channel, raw=raw, disable=disable)

    @cmds.command(
        aliases=("wel",),
        description=welcomeDesc,
        usage="[message] [options]",
        extras=dict(
            example=(
                "welcome Welcome to {guild}, {user(name)}! ch: #userlog",
                "welcome Hello, {user(name)} 👋",
                "welcome raw: on",
                "welcome disable: true",
            ),
            flags={
                "channel": "Set welcome channel",
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
        help="\n`TagScript` is supported!",
    )
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def welcome(self, ctx, *, arguments: str):
        await handleGreetingConfig(ctx, "welcome", arguments=arguments)

    farewellDesc = _("farewell-desc")

    @greetingGroup.command(name=_("farewell"), description=farewellDesc)
    @app_commands.describe(
        channel=_("farewell-arg-channel"),
        raw=_("farewell-arg-raw"),
        disable=_("farewell-arg-disable"),
        message=_("farewell-arg-message"),
    )
    @app_commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def farewellSlash(
        self,
        interaction,
        message: str = None,
        channel: Optional[discord.TextChannel] = None,
        raw: bool = False,
        disable: bool = False,
    ):
        ctx = await Context.from_interaction(interaction)
        await handleGreetingConfig(ctx, "farewell", message=message, channel=channel, raw=raw, disable=disable)

    @cmds.command(
        aliases=("fw",),
        description=farewellDesc,
        usage="[message] [options]",
        extras=dict(
            example=(
                "farewell Bye ch: #userlog",
                "farewell Goodbye, {user(name)}!",
                "farewell raw: on",
                "farewell disable: true",
            ),
            flags={
                "channel": "Set farewell channel",
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
        help="\n`TagScript` is supported!",
    )
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def farewell(self, ctx, *, arguments: str):
        await handleGreetingConfig(ctx, "farewell", arguments=arguments)

    async def handleLogConfig(self, ctx: Context, arguments: LogFlags, type: str):
        """Handle configuration for logs (modlog, purgatory)"""
        # Parsing arguments
        channel = arguments.channel
        disable = arguments.disable

        channelId = MISSING
        if channelId is not MISSING:
            _translated = await ctx.translate(_("log-updated-title", type=type))
            e = ZEmbed.success(title=_translated)

            if channel is not None and not disable:
                channelId = channel.id
                _translated = await ctx.translate(_("log-updated-field-channel"))
                e.add_field(name=_translated, value=channel.mention)
            elif disable is True:
                channelId = None
                _translated = await ctx.translate(_("log-updated-field-status"))
                _translatedDisabled = await ctx.translate(_("log-updated-field-status-disabled"))
                e.add_field(name=_translated, value=f"`{_translatedDisabled}`")

            await self.bot.setGuildConfig(ctx.requireGuild().id, f"{type}Ch", channelId, "GuildChannels")

        else:
            _translated = await ctx.translate(_("log-config-title", guildName=ctx.requireGuild().name, type=type))
            e = ZEmbed.default(ctx, title=_translated)
            channelId = await self.bot.getGuildConfig(ctx.requireGuild().id, f"{type}Ch", "GuildChannels")
            if channelId:
                _translated = await ctx.translate(_("log-config-field-channel"))
                e.add_field(name=_translated, value=f"<#{channelId}>")
            else:
                _translated = await ctx.translate(_("log-config-field-status"))
                _translatedDisabled = await ctx.translate(_("log-config-field-status-disabled"))
                e.add_field(name=_translated, value=f"`{_translatedDisabled}`")

        return await ctx.try_reply(embed=e)

    @cmds.command(
        name=_("modlog"),
        aliases=("ml",),
        description=_("modlog-desc"),
        hybrid=True,
        usage="[channel] [options]",
        extras=dict(
            example=("modlog #modlog", "modlog ch: modlog", "ml disable: on"),
            flags={
                "channel": "Set modlog channel",
                "disable": "Disable modlog",
            },
            perms={
                "bot": "Manage Channels and View Audit Log",
                "user": "Moderator Role or Manage Channels",
            },
        ),
    )
    @app_commands.describe(
        channel=_("modlog-arg-channel"),
        disable=_("modlog-arg-disable"),
    )
    @commands.guild_only()
    @commands.bot_has_guild_permissions(view_audit_log=True, manage_channels=True)
    @checks.mod_or_permissions(manage_channels=True)
    async def modlog(self, ctx, *, arguments: LogFlags):
        await self.handleLogConfig(ctx, arguments, "modlog")

    @cmds.command(
        name=_("purgatory"),
        aliases=("purge", "userlog"),
        description=_("purgatory-desc"),
        hybrid=True,
        usage="[channel] [options]",
        extras=dict(
            example=(
                "purgatory #userlog",
                "purge ch: userlog",
                "userlog disable: on",
            ),
            flags={
                "channel": "Set purgatory channel",
                "disable": "Disable purgatory",
            },
            perms={
                "bot": "Manage Channels",
                "user": "Moderator Role or Manage Channels",
            },
        ),
    )
    @app_commands.describe(
        channel=_("purgatory-arg-channel"),
        disable=_("purgatory-arg-channel"),
    )
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def purgatory(self, ctx, *, arguments: LogFlags):
        await self.handleLogConfig(ctx, arguments, "purgatory")

    @cmds.group(
        name=_("role"),
        description=_("role-desc"),
        hybrid=True,
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
    @commands.guild_only()
    @checks.is_admin()
    async def _role(self, _):
        # Role manager
        pass

    async def updateMutedRoles(
        self,
        ctx: Context,
        role: discord.Role,
    ) -> None:
        """Just loop through channels and overwriting muted role's perm"""
        guild: GuildWrapper
        creator: discord.Member | discord.User
        guild, creator = ctx.requireGuild(), ctx.author

        for channel in guild.channels:
            perms = channel.permissions_for(guild.me)
            if perms.manage_roles:
                overwrite: discord.PermissionOverwrite = channel.overwrites_for(role)

                overwrite.update(
                    # speak=False,
                    send_messages=False,
                )

                localeKey = "role-mute-updated"
                localeData = {"roleName": role.name}
                if creator:
                    localeKey += "-with-reason"
                    localeData["creatorName"] = creator.name

                reason = await ctx.translate(_(localeKey, **localeData))

                await channel.set_permissions(
                    target=role,
                    overwrite=overwrite,
                    reason=reason,
                )

        self.bot.dispatch("muted_role_changed", guild, role)

    @_role.command(
        name="create",
        localeName=_("role-create"),
        aliases=("+", "make"),
        description=_("role-create-desc"),
        usage="(role name) [type: role type]",
        extras=dict(
            perms={
                "bot": "Manage Roles",
                "user": "Administrator",
            },
        ),
    )
    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @checks.is_admin()
    async def roleCreate(self, ctx: Context, *, arguments: RoleCreateFlags):
        name = arguments.name
        if not name:
            return await ctx.error("Name can't be empty!")

        type = (arguments.type_ or "regular").lower()

        if type in ROLE_TYPES:
            async with ctx.loading():
                role = await ctx.requireGuild().create_role(name=name)

                if not role:
                    # TODO: Maybe return a message to tell user that the command fail
                    return

                if type != "regular":
                    await setGuildRole(self.bot, ctx.requireGuild().id, ROLE_TYPES[type], role.id)

                    if any([type == "mute", type == "muted"]):
                        await self.updateMutedRoles(ctx, role)

                e = ZEmbed.success(
                    title=await ctx.translate(_("role-created")),
                    description=await ctx.translate(
                        _("role-properties", roleName=role.name, roleType=type, roleId=str(role.id))
                    ),
                )
                return await ctx.try_reply(embed=e)

        return await ctx.error(
            await ctx.translate(_("role-types-list", roleTypes=", ".join([f"`{type}`" for type in ROLE_TYPES]))),
            title=await ctx.translate(_("role-manage-failed-reason")),
        )

    @_role.command(
        name="set",
        localeName=_("role-set"),
        aliases=("&",),
        description=_("role-set-desc"),
        usage="(role name) (type: role type)",
        extras=dict(
            perms={
                "bot": "Manage Roles",
                "user": "Administrator",
            },
        ),
    )
    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @checks.is_admin()
    async def roleSet(self, ctx: Context, *, arguments: RoleSetFlags):
        role = arguments.role
        type = (arguments.type_ or "regular").lower()
        disallowed = ("regular",)

        if type in ROLE_TYPES and type not in disallowed:
            async with ctx.loading():
                if type != "regular":
                    await setGuildRole(self.bot, ctx.requireGuild().id, ROLE_TYPES[type], role.id)

                    if any([type == "mute", type == "muted"]):
                        await self.updateMutedRoles(ctx, role)

                e = ZEmbed.success(
                    title=await ctx.translate(_("role-created")),
                    description=await ctx.translate(
                        _("role-properties", roleName=role.name, roleType=type, roleId=str(role.id))
                    ),
                )
                return await ctx.try_reply(embed=e)

        return await ctx.error(
            await ctx.translate(
                _("role-types-list", roleTypes=", ".join([f"`{type}`" for type in ROLE_TYPES if type not in disallowed]))
            ),
            title=await ctx.translate(_("role-manage-failed-reason")),
        )

    @_role.command(
        name="types",
        localeName=_("role-types"),
        description=_("role-types-desc"),
    )
    async def roleTypes(self, ctx: Context):
        e = ZEmbed.minimal(
            title=await ctx.translate(_("role-types-title")),
            description="\n".join("- `{}`".format(role) for role in ROLE_TYPES),
        )
        e.set_footer(text=await ctx.translate(_("role-types-footer")))
        return await ctx.try_reply(embed=e)

    @commands.command(
        description="Set auto role",
        help=".\nA role that will be given to a new member upon joining",
        usage="(role name)",
        extras=dict(
            example=("autorole @Member",),
            perms={
                "bot": "Manage Roles",
                "user": "Administrator",
            },
        ),
    )
    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @checks.is_admin()
    async def autorole(self, ctx, name: Union[discord.Role, str]):
        # This is just an alias command, don't need to be added as slash
        await ctx.try_invoke(
            self.roleCreate if isinstance(name, str) else self.roleSet,
            arguments=f"{getattr(name, 'id', name)} type: member",
        )

    @cmds.command(
        name=_("announcement"),
        description=_("announcement-desc"),
        hybrid=True,
        extras=dict(
            example=("announcement #announcement",),
            perms={
                "bot": None,
                "user": "Manage Channels",
            },
        ),
    )
    @app_commands.describe(channel=_("announcement-arg-channel"))
    @commands.guild_only()
    @checks.is_mod()
    async def announcement(self, ctx, channel: discord.TextChannel):
        await self.bot.setGuildConfig(ctx.guild.id, "announcementCh", channel.id, "GuildChannels")
        return await ctx.success(
            await ctx.translate(_("announcement-updated-channel", channelMention=channel.mention)),
            title=await ctx.translate(_("announcement-updated")),
        )
