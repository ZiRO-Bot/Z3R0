"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import Optional, Union

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import MISSING

from ...core import checks, flags
from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.mixin import CogMixin
from ...utils.format import separateStringFlags
from ...utils.other import setGuildRole
from ._flags import ROLE_TYPES, LogFlags, RoleCreateFlags, RoleSetFlags


class Greeting(discord.ui.Modal, title="Greeting"):
    # TODO - Move this into _view.py
    message = discord.ui.TextInput(
        label="Message", placeholder="Welcome, {user(mention)}! {react: 👋}", style=discord.TextStyle.paragraph
    )

    # TODO - hopefully discord will add channel input soon into modal
    #        for now i'll comment this
    # channel = discord.ui.TextInput(
    #     label="Channel",
    #     placeholder="336642139381301249",
    # )

    def __init__(
        self,
        context: Context,
        type: str,
        *,
        defaultMessage: Optional[str] = None,
    ) -> None:
        super().__init__(title=type.title())
        self.context = context
        self.type = type
        self.message.default = defaultMessage

    async def callback(self):
        await handleGreetingConfig(self.context, self.type, message=self.message)  # type: ignore

    async def on_submit(self, inter: discord.Interaction):
        await self.callback()
        return await inter.response.defer()


async def handleGreetingConfig(
    ctx: Context,
    type: str,
    *,
    arguments=MISSING,
    message: str = None,
    raw: bool = False,
    disable: bool = False,
    channel: discord.TextChannel = None,
):
    """Handle welcome and farewell configuration."""
    guild: discord.Guild | None = ctx.guild
    if not guild:
        raise RuntimeError

    changeMsg = False

    if arguments is None:
        # TODO - Revisit once more input introduced to modals
        # TODO - Timeout + disable the button
        defMsg = await ctx.bot.getGuildConfig(guild.id, f"{type}Msg")

        def makeCallback():
            async def callback(interaction: discord.Interaction):
                modal = Greeting(ctx, type, defaultMessage=defMsg)
                await interaction.response.send_modal(modal)

            return callback

        btn = discord.ui.Button(label=f"Set {type} config")
        btn.callback = makeCallback()
        view = discord.ui.View()
        view.add_item(btn)

        await ctx.try_reply(
            "This feature currently not yet available on Mobile!\n"
            "If you're on Mobile, please do `{}{} "
            "[message] [options]` instead".format(ctx.clean_prefix, type),
            view=view,
        )
        return
    elif arguments is not MISSING:
        message, args = separateStringFlags(arguments)

        parsed = await flags.GreetingFlags.convert(ctx, args)

        # Parsed value from flags
        disable = parsed.disable
        raw = parsed.raw
        channel = parsed.channel
        message = " ".join([message.strip()] + parsed.messages).strip()

    if not raw and not disable and message:
        changeMsg = True

    e = ZEmbed.success(
        title=("Welcome" if type == "welcome" else "Farewell") + " config has been updated",
    )

    if disable is True:
        await ctx.bot.setGuildConfig(guild.id, f"{type}Ch", None, "GuildChannels")
        e.add_field(name="Status", value="`Disabled`")
        return await ctx.try_reply(embed=e)

    if raw is True:
        message = await ctx.bot.getGuildConfig(guild.id, f"{type}Msg")
        return await ctx.try_reply(discord.utils.escape_markdown(str(message)))

    if changeMsg:
        await ctx.bot.setGuildConfig(guild.id, f"{type}Msg", message)
        e.add_field(name="Message", value=message, inline=False)

    if channel is not None:
        await ctx.bot.setGuildConfig(guild.id, f"{type}Ch", channel.id, "GuildChannels")
        e.add_field(name="Channel", value=channel.mention)

    return await ctx.try_reply(embed=e)


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

    welcomeDesc = "Set welcome message and/or channel\n`TagScript` is supported!"

    @greetingGroup.command(name="welcome", description=welcomeDesc)
    @app_commands.describe(
        channel="Channel where welcome messages will be sent",
        raw="Get current welcome message in raw mode (Useful for editing, other options is ignored when used!)",
        disable="Disable welcome event",
        message="Message that will be sent to the welcome channel",
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

    @commands.command(
        aliases=("wel",),
        brief="Set welcome message and/or channel",
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
        description="Set welcome message and/or channel\n`TagScript` is supported!",
    )
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def welcome(self, ctx, *, arguments: str):
        await handleGreetingConfig(ctx, "welcome", arguments=arguments)

    farewellDesc = "Set farewell message and/or channel\n`TagScript` is supported!"

    @greetingGroup.command(name="farewell", description=farewellDesc)
    @app_commands.describe(
        channel="Channel where farewell messages will be sent",
        raw="Get current farewell message in raw mode (Useful for editing, other options is ignored when used!)",
        disable="Disable farewell event",
        message="Message that will be sent to the farewell channel",
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

    @commands.command(
        aliases=("fw",),
        brief="Set farewell message and/or channel",
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
    )
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def farewell(self, ctx, *, arguments: str):
        await handleGreetingConfig(ctx, "farewell", arguments=arguments)

    async def handleLogConfig(self, ctx, arguments: LogFlags, type: str):
        """Handle configuration for logs (modlog, purgatory)"""
        # Parsing arguments
        channel = arguments.channel
        disable = arguments.disable

        e = ZEmbed.success(title=("Modlog" if type == "modlog" else "Purgatory") + " config has been updated")

        channelId = MISSING
        if channel is not None and not disable:
            channelId = channel.id
            e.add_field(name="Channel", value=channel.mention)
        elif disable is True:
            channelId = None
            e.add_field(name="Status", value="`Disabled`")

        if channelId is not MISSING:
            await self.bot.setGuildConfig(ctx.guild.id, f"{type}Ch", channelId, "GuildChannels")
        else:
            channelId = await self.bot.getGuildConfig(ctx.guild.id, f"{type}Ch", "GuildChannels")
            if channelId:
                e.add_field(name="Channel", value=f"<#{channelId}>")
            else:
                e.add_field(name="Status", value="`Disabled`")

        return await ctx.try_reply(embed=e)

    @commands.hybrid_command(
        aliases=("ml",),
        brief="Set modlog channel",
        description="Set modlog channel",
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
        channel="Channel where modlogs will be sent",
        disable="Disable modlog",
    )
    @commands.guild_only()
    @commands.bot_has_guild_permissions(view_audit_log=True, manage_channels=True)
    @checks.mod_or_permissions(manage_channels=True)
    async def modlog(self, ctx, *, arguments: LogFlags):
        await self.handleLogConfig(ctx, arguments, "modlog")

    @commands.hybrid_command(
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
        channel="Channel where deleted/edited messages will be sent",
        disable="Disable purgatory",
    )
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def purgatory(self, ctx, *, arguments: LogFlags):
        await self.handleLogConfig(ctx, arguments, "purgatory")

    @commands.hybrid_group(
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
    @commands.guild_only()
    @checks.is_admin()
    async def _role(self, _):
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
            perms = channel.permissions_for(guild.me)
            if perms.manage_roles:
                overwrite: discord.PermissionOverwrite = channel.overwrites_for(role)

                overwrite.update(
                    # speak=False,
                    send_messages=False,
                )

                reason = "Mute role set to {}".format(role.name)
                if creator:
                    reason += " by {}".format(creator)

                await channel.set_permissions(
                    target=role,
                    overwrite=overwrite,
                    reason=reason,
                )

        self.bot.dispatch("muted_role_changed", guild, role)

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
    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @checks.is_admin()
    async def roleCreate(self, ctx, *, arguments: RoleCreateFlags):
        name = arguments.name
        if not name:
            return await ctx.error("Name can't be empty!")

        type = arguments.type_ or "regular"

        if (type := type.lower()) in ROLE_TYPES:
            msg = await ctx.try_reply(
                embed=ZEmbed.loading(),
            )

            role = await ctx.guild.create_role(name=name)

            if not role:
                # TODO: Maybe return a message to tell user that the command fail
                return

            if type != "regular":
                await setGuildRole(self.bot, ctx.guild.id, ROLE_TYPES[type], role.id)

                if any([type == "mute", type == "muted"]):
                    await self.updateMutedRoles(ctx.guild, role, ctx.author)

            e = ZEmbed.success(
                title="SUCCESS: Role has been created",
                description="**Name**: {}\n**Type**: `{}`\n**ID**: `{}`".format(role.name, type, role.id),
            )
            return await msg.edit(embed=e)

        return await ctx.error(
            "Available role type: {}".format(", ".join([f"`{type}`" for type in ROLE_TYPES])),
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
    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @checks.is_admin()
    async def roleSet(self, ctx, *, arguments: RoleSetFlags):
        role = arguments.role
        type = arguments.type_
        disallowed = ("regular",)

        if (type := type.lower()) in ROLE_TYPES and type not in disallowed:
            msg = await ctx.try_reply(
                embed=ZEmbed.loading(),
            )

            if type != "regular":
                await setGuildRole(self.bot, ctx.guild.id, ROLE_TYPES[type], role.id)

                if any([type == "mute", type == "muted"]):
                    await self.updateMutedRoles(ctx.guild, role, ctx.author)

            e = ZEmbed.success(
                title="SUCCESS: Role has been modified",
                description="**Name**: {}\n**Type**: `{}`\n**ID**: `{}`".format(role.name, type, role.id),
            )
            return await msg.edit(embed=e)

        return await ctx.error(
            "Available role type: {}".format(", ".join([f"`{type}`" for type in ROLE_TYPES if type not in disallowed])),
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
        description=("Set auto role.\n" "A role that will be given to a new member upon joining"),
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
        await ctx.try_invoke(
            self.roleCreate if isinstance(name, str) else self.roleSet,
            arguments=f"{getattr(name, 'id', name)} type: member",
        )

    @commands.hybrid_command(
        brief="Set announcement channel",
        extras=dict(
            example=("announcement #announcement",),
            perms={
                "bot": None,
                "user": "Manage Channels",
            },
        ),
    )
    @app_commands.describe(channel="Channel where announcements will be sent")
    @commands.guild_only()
    @checks.is_mod()
    async def announcement(self, ctx, channel: discord.TextChannel):
        await self.bot.setGuildConfig(ctx.guild.id, "announcementCh", channel.id, "GuildChannels")
        return await ctx.success(
            f"**Channel**: {channel.mention}",
            title="Announcement channel has been updated",
        )
