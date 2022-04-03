"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from typing import Callable, Optional, Union

import discord
from discord.ext import commands
from discord.utils import MISSING

from ...core import checks, flags
from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.mixin import CogMixin
from ...utils.format import separateStringFlags
from ...utils.other import setGuildRole


class Greeting(discord.ui.Modal, title="Greeting"):
    # TODO - Move this into _view.py
    message = discord.ui.TextInput(
        label="Message", placeholder="Welcome, {user(mention)}! {react: 👋}", style=discord.TextStyle.paragraph
    )

    # TODO - hopefully discord will add channel input soon into modal
    #        for now i'll comment this
    # channel = discord.ui.TextInput(
    #     label="Channel",
    #     placeholder="794344590618394625",
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
        await handleGreetingConfig(self.context, self.type, message=self.message)

    async def on_submit(self, inter: discord.Interaction):
        await self.callback()
        return await inter.response.defer()


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


async def handleGreetingConfig(
    ctx: Context, type: str, *, arguments=MISSING, message: str = None, disable=False, channel=None
):
    """Handle welcome and farewell configuration."""
    raw = False
    if arguments is None:
        # TODO - Revisit once more input introduced to modals
        # TODO - Timeout + disable the button
        defMsg = await ctx.bot.getGuildConfig(ctx.guild.id, f"{type}Msg")

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
        changeMsg = False
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
        await ctx.bot.setGuildConfig(ctx.guild.id, f"{type}Ch", None, "GuildChannels")
        e.add_field(name="Status", value="`Disabled`")
        return await ctx.try_reply(embed=e)

    if raw is True:
        message = await ctx.bot.getGuildConfig(ctx.guild.id, f"{type}Msg")
        return await ctx.try_reply(discord.utils.escape_markdown(str(message)))

    if changeMsg and message:
        await ctx.bot.setGuildConfig(ctx.guild.id, f"{type}Msg", message)
        e.add_field(name="Message", value=message, inline=False)

    if channel is not None:
        await ctx.bot.setGuildConfig(ctx.guild.id, f"{type}Ch", channel.id, "GuildChannels")
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
    )
    @checks.mod_or_permissions(manage_channels=True)
    async def welcome(self, ctx, *, arguments: str = None):
        await handleGreetingConfig(ctx, "welcome", arguments=arguments)

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
    @checks.mod_or_permissions(manage_channels=True)
    async def farewell(self, ctx, *, arguments: str = None):
        await handleGreetingConfig(ctx, "farewell", arguments=arguments)

    async def handleLogConfig(self, ctx, arguments, type: str):
        """Handle configuration for logs (modlog, purgatory)"""
        # Parsing arguments
        channel, args = separateStringFlags(arguments)
        channel = channel.strip()
        if channel != "":
            channel = await commands.TextChannelConverter().convert(ctx, channel)
        else:
            channel = None

        parsed = await flags.LogConfigFlags.convert(ctx, args)

        disable = parsed.disable

        e = ZEmbed.success(title=("Modlog" if type == "modlog" else "Purgatory") + " config has been updated")

        if parsed.channel is not None:
            channel = parsed.channel

        channelId = MISSING
        if channel is not None and not disable:
            channelId = channel.id
            e.add_field(name="Channel", value=channel.mention)
        else:
            channelId = None
            e.add_field(name="Status", value="`Disabled`")

        if channelId is not MISSING:
            await self.bot.setGuildConfig(ctx.guild.id, f"{type}Ch", channelId, "GuildChannels")
        else:
            e.description = "Nothing changed."

        return await ctx.try_reply(embed=e)

    @commands.command(
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
    @commands.bot_has_guild_permissions(view_audit_log=True, manage_channels=True)
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
                "channel": "Set purgatory channel",
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
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def roleCreate(self, ctx, *, arguments):
        name, args = separateStringFlags(arguments)
        parsed = await flags.RoleCreateFlags.convert(ctx, args)

        name = " ".join([name.strip()] + parsed.nameList).strip()
        if not name:
            return await ctx.error("Name can't be empty!")

        type = parsed.type_ or "regular"

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
    async def roleSet(self, ctx, *, arguments):
        roleArg, args = separateStringFlags(arguments)
        parsed = await flags.RoleSetFlags.convert(ctx, args)
        if parsed.role:
            role = parsed.role
        else:
            role = await commands.RoleConverter().convert(ctx, roleArg.strip())

        if not role:
            # should already handled by command.RoleConverter but just incase
            return

        type = parsed.type_

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
    @commands.bot_has_guild_permissions(manage_roles=True)
    @checks.is_admin()
    async def autorole(self, ctx, name: Union[discord.Role, str]):
        await ctx.try_invoke(
            self.roleCreate if isinstance(name, str) else self.roleSet,
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
    @checks.is_mod()
    async def announcement(self, ctx, channel: discord.TextChannel):
        await self.bot.setGuildConfig(ctx.guild.id, "announcementCh", channel.id, "GuildChannels")
        return await ctx.success(
            f"**Channel**: {channel.mention}",
            title="Announcement channel has been updated",
        )
