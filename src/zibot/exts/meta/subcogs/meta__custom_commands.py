"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import difflib
import re
from typing import TYPE_CHECKING, Any, Iterable

import discord
from discord.ext import commands

from ....core import checks, db
from ....core.context import Context
from ....core.data import CacheListProperty, CacheUniqueViolation
from ....core.embed import ZEmbed
from ....core.guild import CCMode, GuildWrapper
from ....core.menus import ZChoices, choice
from ....core.mixin import CogMixin
from ....utils import utcnow
from ....utils.format import formatCmdName
from .._checks import hasCCPriviledge
from .._custom_command import CustomCommand, ManagedCustomCommand
from .._errors import CCommandAlreadyExists, CCommandNoPerm, CCommandNotFound
from .._flags import CmdManagerFlags
from .._utils import getDisabledCommands


if TYPE_CHECKING:
    from ....core.bot import ziBot
    from .._help import CustomHelp


GIST_REGEX = re.compile(r"http(?:s)?:\/\/gist\.github(?:usercontent)?\.com\/.*\/(\S*)(?:\/)?")
PASTEBIN_REGEX = re.compile(r"http(?:s)?:\/\/pastebin.com\/(?:raw\/)?(\S*)")


DIFFER = difflib.Differ()


class MetaCustomCommands(commands.Cog, CogMixin):
    """Meta subcog for custom commands"""

    def __init__(self, bot: ziBot):
        super().__init__(bot)

        # Cache for disabled commands
        self.bot.cache.add(
            "disabled",
            cls=CacheListProperty,
            unique=True,
        )

    # TODO: Separate tags from custom command
    @commands.group(
        aliases=("cmd", "tag", "script"),
        description="Manage commands",
        help="\n\n**NOTE**: Custom Commands only available for guilds/servers!",
    )
    @commands.guild_only()
    async def command(self, _):
        pass

    @command.command(aliases=("exec", "execute"), description="Execute a custom command")
    async def run(self, ctx, command: CustomCommand | str, argument: str = ""):
        if isinstance(command, str):
            command = await CustomCommand.get(ctx, command)
        return await command.execute(ctx, argument)

    @command.command(
        name="source",
        aliases=("src", "raw"),
        description="Get raw content of a custom command",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _source(self, ctx, command: CustomCommand):
        return await command.execute(ctx, raw=True)

    async def addCmd(self, ctx, name: str, content: str, **kwargs):
        """Add cmd to database"""
        cmd = await db.Commands.create(
            name=name,
            content=content,
            ownerId=ctx.author.id,
            createdAt=utcnow(),
            type=kwargs.get("type", "text"),
            url=kwargs.get("url"),
        )
        lookup = await db.CommandsLookup.create(cmd_id=cmd.id, name=name, guild_id=ctx.guild.id)
        if cmd and lookup:
            return cmd.id, lookup.name
        return (None,) * 2

    def getValidLink(self, url):
        # TODO: Find better way to parse valid link
        # TODO: Add support for hastebin and mystb.in
        # Link will either be None, pastebin, or gist
        # TODO: Drop pastebin support replace it with hastebin
        link = None

        url = url.rstrip("/")

        # Regex stuff
        # TODO: Find better way of finding "valid" url
        group = GIST_REGEX.fullmatch(str(url))
        if group:
            if group.group(1) == "raw":
                link = group.group(0)
            else:
                link = group.group(0) + "/raw"
        else:
            group = PASTEBIN_REGEX.fullmatch(str(url))
            if not group:
                raise commands.BadArgument("<{}> is not a valid url!".format(url))
            link = "https://pastebin.com/raw/" + group.group(1)
        return link

    async def isCmdExist(self, ctx, name: str):
        """Check if command already exists"""
        rows = await db.CommandsLookup.filter(name=name, guild__id=ctx.guild.id).first()
        if rows:
            raise CCommandAlreadyExists(name)

    @command.command(
        name="import",
        aliases=("++",),
        description="Import a custom command from pastebin/gist.github",
        extras=dict(
            example=(
                "command import pastebin-cmd https://pastebin.com/ZxvGqEAs",
                "command ++ gist " "https://gist.github.com/null2264/87c89d2b5e2453529e29c2cae3b57729",
            ),
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    @hasCCPriviledge()
    async def _import(self, ctx: Context, name: str, *, url: str):
        # NOTE: This command will only support pastebin and gist.github,
        # maybe also hastebin.
        try:
            link = self.getValidLink(url)
        except commands.BadArgument as exc:
            return await ctx.try_reply(str(exc))

        # Check if command already exists
        await self.isCmdExist(ctx, name)

        content = None
        async with ctx.session.get(link) as request:
            content = await request.text()

        lastInsert, lastLastInsert = await self.addCmd(
            ctx,
            name,
            content or "`ERROR`: Failed to retrieve command",
            type="import",
            url=link,
        )
        if lastInsert and lastLastInsert:
            await ctx.success(
                "**Source**: <{}>".format(url),
                title="`{}` has been imported".format(name),
            )

    @command.command(
        name="add",
        aliases=("+", "create"),
        description="Create a new custom command",
        extras=dict(
            example=(
                "command add example-cmd Just an example",
                "cmd + hello Hello World!",
            ),
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    @hasCCPriviledge()
    async def _add(self, ctx, name: str, *, content: str):
        # Check if command already exists
        await self.isCmdExist(ctx, name)

        # Adding command to database
        lastInsert, lastLastInsert = await self.addCmd(ctx, name, content)
        if lastInsert and lastLastInsert:
            await ctx.success(title="Command `{}` has been created".format(name))

    @command.command(
        name="update-url",
        aliases=("&u", "set-url"),
        description="Update imported command's source url",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def update_url(self, ctx: Context, name: str, url: str):
        # NOTE: Can only be run by cmd owner or guild mods/owner
        command = await CustomCommand.get(ctx, name)

        perm = await command.canManage(ctx)
        if not perm:
            raise CCommandNoPerm

        if not command.url:
            # Incase someone try to update `text` command
            return await ctx.error(
                "Please use `{}command edit` instead!".format(ctx.clean_prefix),
                title="`{}` is not imported command!".format(name),
            )
        try:
            link = self.getValidLink(url)
        except commands.BadArgument as exc:
            return await ctx.try_reply(str(exc))

        if link == command.url:
            return await ctx.try_reply("Nothing changed.")

        await db.Commands.filter(id=command.id).update(url=link)

        return await ctx.success(
            "\nYou can do `{}command update {}` to update the content".format(ctx.clean_prefix, name),
            title="`{}` url has been set to <{}>".format(name, url),
        )

    async def updateCommandContent(self, _: Context, command: ManagedCustomCommand, content):
        """Update command's content"""
        update = await db.Commands.filter(id=command.id).update(content=content)
        if update:
            return True
        return False

    @command.command(
        aliases=("&&", "pull"),
        description="Update imported command's content",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def update(self, ctx: Context, command: ManagedCustomCommand):
        # NOTE: Can only be run by cmd owner or guild mods/owner

        # For both checking if command exists and
        # getting its content for comparation later on
        if not command.url:
            # Incase someone try to update `text` command
            return await ctx.error(
                "Please use `{}command edit` instead!".format(ctx.clean_prefix),
                title="`{}` is not imported command!".format(command.name),
            )

        content = None
        async with ctx.session.get(command.url) as request:
            content = await request.text()

        # Compare and get changes
        addition = 0
        deletion = 0
        for changes in DIFFER.compare(command.content, content or ""):
            if changes.startswith("- "):
                deletion += 1
            if changes.startswith("+ "):
                addition += 1
        if not addition and not deletion:
            # Nothing changed, so let's just send a message
            return await ctx.success(
                "\n[**Note**]: It takes awhile for the site to be updated!",
                title="Already up to date.",
            )

        update = await self.updateCommandContent(ctx, command, content)
        if update:
            return await ctx.success(
                ("`[+]` {} Additions\n".format(addition) + "`[-]` {} Deletions".format(deletion)),
                title="Command `{}` has been update\n".format(command.name),
            )

    @command.command(
        aliases=("/",),
        description="Add an alias to a custom command",
        usage="(command name) (alias)",
        extras=dict(
            example=(
                "command alias example-cmd test-cmd",
                "command alias leaderboard board",
            ),
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def alias(self, ctx, command: ManagedCustomCommand, alias: str):
        if alias == command.name:
            return await ctx.error("Alias can't be identical to original name!")
        if alias in command.aliases:
            return await ctx.error("Alias `{}` already exists!".format(alias))

        insert = await db.CommandsLookup.create(cmd_id=command.id, name=alias, guild_id=ctx.guild.id)

        if insert:
            return await ctx.success(title="Alias `{}` for `{}` has been created".format(alias, command))

    @command.command(
        name="edit",
        description="Edit custom command's content",
        help="\n\nAlias for `command set content`",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def cmdEdit(self, ctx, command: ManagedCustomCommand, *, content):
        await self.setContent(ctx, command, content=content)

    @command.group(
        name="set",
        description="Edit custom command's property",
        help="\n\nBy default, will edit command's content when there is no subcommand specified",
        extras=dict(
            example=(
                "cmd set category example-cmd info",
                "cmd edit cat test-embed unsorted",
                "command & mode 0",
                "command & example-cmd This is an edit",
            )
        ),
    )
    async def cmdSet(self, _):
        pass

    @cmdSet.command(
        name="content",
        aliases=("cont",),
        description="Edit custom command's content",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def setContent(self, ctx, command: ManagedCustomCommand, *, content):
        update = await self.updateCommandContent(ctx, command, content)
        if update:
            return await ctx.success(title="Command `{}` has been edited\n".format(command))

    @cmdSet.command(
        name="url",
        aliases=("u",),
        description="Alias for `command update-url`",
    )
    async def setUrl(self, ctx, name: str, url: str):
        await self.update_url(ctx, name, url)

    @cmdSet.command(
        name="alias",
        description="Alias for `command alias`",
    )
    async def setAlias(self, ctx, command: ManagedCustomCommand, alias: str):
        await self.alias(ctx, command, alias)

    @cmdSet.command(
        name="category",
        aliases=("cat", "mv"),
        usage="(command) (category)",
        description="Move a custom command to a category",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def setCategory(self, ctx, command: ManagedCustomCommand, category: str):
        category = category.lower()

        availableCats = [cog.qualified_name.lower() for cog in ctx.bot.cogs.values() if getattr(cog, "cc", False)]
        if category not in availableCats:
            return await ctx.error(title="Invalid category")

        if command.category == category:
            return await ctx.success(title="{} already in {}!".format(command, category))

        update = await db.Commands.filter(id=command.id).update(category=category)

        if update:
            return await ctx.success(title="{}'s category has been set to {}!".format(command, category))

    @cmdSet.command(
        name="mode",
        description="Set custom command 'mode'",
        help=(
            "\n\n__**Modes:**__\n> `0`: Mods-only\n> "
            "`1`: Member can add command but only able to manage their own "
            "command\n> `2`: Member can add AND manage custom command (Anarchy "
            "mode)"
        ),
        extras=dict(
            example=(
                "command set mode 0",
                "cmd set mode 1",
                "cmd set mode 2",
            ),
            perms={
                "bot": None,
                "user": "Moderator Role or Manage Guilds",
            },
        ),
    )
    @checks.is_mod()
    async def setMode(self, ctx, mode: int):
        if mode > 2:
            return await ctx.error(title="There's only 3 available mode! (0, 1, 2)")

        result = await self.bot.setGuildConfig(ctx.guild.id, "ccMode", mode)
        if result is not None:
            return await ctx.success(
                str(CCMode(mode)),
                title="Custom command mode has been set to `{}`".format(mode),
            )

    @command.command(
        aliases=("-", "rm"),
        description="Remove a custom command",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def remove(self, ctx, command: ManagedCustomCommand):
        isAlias = command.invokedName in command.aliases
        if isAlias:
            await db.CommandsLookup.filter(name=command.invokedName, guild_id=ctx.guild.id).delete()
        else:
            # NOTE: Aliases will be deleted automatically
            await db.Commands.filter(id=command.id).delete()

        return await ctx.success(title="{} `{}` has been removed".format("Alias" if isAlias else "Command", command.name))

    async def disableEnableHelper(
        self,
        ctx,
        name,
        /,
        *,
        action: str,
        isMod: bool,
        immuneRoot: Iterable[str] = ("help", "command"),
    ) -> tuple[Any, str] | None:
        """Helper for `command disable` and `command enable`

        - Find built-in command, custom command, and category
        - Give choices to user when there's more than 1 type is found
          with identical name
        - Return user's choice (or raise RuntimeError when user
          doesn't choose anything)
        """
        foundList = []  # contains built-in and custom command, also category

        # only mods allowed to disable/enable built-in commands
        if isMod:
            # find built-in command
            cmd = ctx.bot.get_command(str(name))
            if cmd:
                cmdName = formatCmdName(cmd)

                if str(cmd.root_parent or cmdName) not in immuneRoot:
                    # check if command root parent is immune
                    foundList.append(choice(f"{cmdName} (Built-in Command)", (cmdName, "command")))

            # find category
            category = ctx.bot.get_cog(str(name))
            if category:
                foundList.append(choice(f"{category.qualified_name} (Category)", (category, "category")))

        # find custom command
        try:
            cc = await CustomCommand.get(ctx, name)
        except CCommandNotFound:
            pass
        else:
            foundList.append(choice(f"{cc.name} (Custom Command)", (cc, "custom")))

        if len(foundList) <= 0:
            # Nothing found, abort
            return await ctx.error(f"No command/category called '{name}' can be {action}d")

        chosen = None

        if len(foundList) == 1:
            # default chosen value
            chosen = foundList[0].value
        else:
            # give user choices, since there's more than 1 type is found
            choices = ZChoices(ctx, foundList)
            msg = await ctx.try_reply(f"Which one do you want to {action}?", view=choices)
            await choices.wait()
            await msg.delete()
            chosen = choices.value

        if not chosen:
            # nothing is chosen, abort (only happened when choices triggered)
            return

        return chosen

    @command.command(
        description="Disable a command",
        help=(
            "\n\nSupport both custom and built-in command.\n\n"
            "**New in `3.3.0`**: Removed options/flags. You'll get choices "
            "when you can disable more than 1 type of command (or category)."
        ),
        extras=dict(
            example=(
                "command disable example",
                "cmd disable weather",
                "command disable info",
                "cmd disable test",
            ),
            perms={
                "bot": None,
                "user": "Depends on custom command mode or (Moderator Role or Manage Guild)",
            },
        ),
        usage="(command/category name)",
    )
    async def disable(self, ctx, *, name):
        if not name:
            return await ctx.error("You need to specify the command's name!")

        isMod = await checks.isMod(ctx)

        successMsg = "`{}` has been disabled"
        alreadyMsg = "`{}` already disabled!"
        immuneRoot = ("help", "command")

        chosen = await self.disableEnableHelper(ctx, name, action="disable", isMod=isMod, immuneRoot=immuneRoot)

        if not chosen or isinstance(chosen, discord.Message):
            return

        mode = chosen[1]

        if mode == "category":
            disabled = await getDisabledCommands(self.bot, ctx.guild.id)

            added = []
            added.extend([c.name for c in chosen[0].get_commands() if c.name not in immuneRoot and c.name not in disabled])

            if not added:
                return await ctx.error(title="No commands succesfully disabled")

            self.bot.cache.disabled.extend(ctx.guild.id, added)  # type: ignore

            await db.Disabled.bulk_create([db.Disabled(guild_id=ctx.guild.id, command=str(cmd)) for cmd in added])

            return await ctx.success(title="`{}` commands has been disabled".format(len(added)))

        if mode == "custom":
            command = chosen[0]
            perm = await command.canManage(ctx)
            if not perm:
                raise CCommandNoPerm

            if not command.enabled:
                return await ctx.error(title=alreadyMsg.format(name))

            await db.Commands.filter(id=command.id).update(enabled=False)
            return await ctx.success(title=successMsg.format(name))

        if mode == "command":
            cmdName = chosen[0]

            # Make sure disable command is cached from database
            await getDisabledCommands(self.bot, ctx.guild.id)

            try:
                self.bot.cache.disabled.append(ctx.guild.id, cmdName)  # type: ignore
            except CacheUniqueViolation:
                # check if command already disabled
                return await ctx.error(title=alreadyMsg.format(cmdName))

            await db.Disabled.create(guild_id=ctx.guild.id, command=cmdName)
            return await ctx.success(title=successMsg.format(cmdName))

    @command.command(
        description="Enable a command",
        help=(
            "\n\nSupport both custom and built-in command.\n\n"
            "**New in `3.3.0`**: Removed options/flags. You'll get choices "
            "when you can enable more than 1 type of command (or category)."
        ),
        extras=dict(
            example=(
                "command enable example",
                "cmd enable weather",
                "cmd enable info",
                "cmd enable test",
            ),
            perms={
                "bot": None,
                "user": "Depends on custom command mode or (Moderator Role or Manage Guild)",
            },
        ),
        usage="(name)",
    )
    async def enable(self, ctx, *, arguments: CmdManagerFlags):
        name = arguments.string
        if not name:
            return await ctx.error("You need to specify the command's name!")

        isMod = await checks.isMod(ctx)

        successMsg = "`{}` has been enabled"
        alreadyMsg = "`{}` already enabled!"

        chosen = await self.disableEnableHelper(ctx, name, action="enable", isMod=isMod, immuneRoot=[])

        if not chosen or isinstance(chosen, discord.Message):
            return

        mode = chosen[1]

        if mode == "category":
            disabled = await getDisabledCommands(self.bot, ctx.guild.id)

            removed = []
            for c in chosen[0].get_commands():
                if c.name not in disabled:
                    continue
                self.bot.cache.disabled.remove(ctx.guild.id, c.name)  # type: ignore
                removed.append(c.name)

            if not removed:
                return await ctx.error(title="No commands succesfully enabled")

            filtered = db.Disabled.filter(guild_id=ctx.guild.id)
            for cmd in removed:
                await filtered.filter(command=cmd).delete()

            return await ctx.success(title="`{}` commands has been enabled".format(len(removed)))

        if mode == "custom":
            command = chosen[0]
            perm = await command.canManage(ctx)
            if not perm:
                raise CCommandNoPerm

            if command.enabled:
                return await ctx.error(title=alreadyMsg.format(name))

            await db.Commands.filter(id=command.id).update(enabled=True)
            return await ctx.success(title=successMsg.format(name))

        if mode == "command":
            cmdName = chosen[0]

            try:
                self.bot.cache.disabled.remove(ctx.guild.id, cmdName)  # type: ignore
            except (ValueError, IndexError):
                # command already enabled
                return await ctx.error(title=alreadyMsg.format(cmdName))

            await db.Disabled.filter(guild_id=ctx.guild.id, command=cmdName).delete()

            return await ctx.success(title=successMsg.format(cmdName))

    @command.command(
        aliases=("?",),
        description="Show command's information",
        help=".\n\nAlias for `help`",
        extras=dict(
            example=(
                "command info help",
                "cmd info command",
                "cmd ? example-cmd",
                "cmd ? cmd filters: custom built-in",
            )
        ),
    )
    async def info(self, ctx, *, name: str = None):
        cmd: CustomHelp = ctx.bot.help_command
        cmd = cmd.copy()
        cmd.context = ctx
        await cmd.command_callback(ctx, arguments=name)

    @command.command(name="list", aliases=("ls",), description="Show all custom commands")
    async def cmdList(self, ctx: Context):
        cmd: CustomHelp = ctx.bot.help_command
        cmd = cmd.copy()
        cmd.context = ctx
        await cmd.command_callback(ctx, arguments="filter: custom")

    @command.command(name="mode", description="Show current custom command mode")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def cmdMode(self, ctx: Context):
        mode = await ctx.requireGuild().getCCMode()

        e = ZEmbed.minimal(title="Current Mode: `{}`".format(str(mode.value)), description=mode)
        return await ctx.try_reply(embed=e)

    @command.command(name="modes", description="Show all different custom command modes")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def cmdModes(self, ctx):
        e = ZEmbed.minimal(
            title="Custom Command Modes",
            fields=[("Mode `{}`".format(mode.value), str(mode)) for mode in list(CCMode)],
        )
        e.set_footer(text="Use `{}command set mode [mode]` to set the mode!".format(ctx.clean_prefix))
        return await ctx.try_reply(embed=e)

    @commands.command(
        name="commands",
        aliases=("cmds",),
        description="Show all custom commands. Alias for `command list`",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _commands(self, ctx):
        await ctx.try_invoke(self.cmdList)
