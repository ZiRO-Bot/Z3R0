"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from enum import Enum

import discord
from discord.ext import commands

import tse

from ...core import checks, db
from ...core.context import Context
from ...core.errors import CCommandDisabled, CCommandNotFound, CCommandNotInGuild
from ...utils import tseBlocks
from ...utils.format import CMDName
from ...utils.other import reactsToMessage, utcnow


_blocks = [
    tse.AssignmentBlock(),
    tse.EmbedBlock(),
    tse.LooseVariableGetterBlock(),
    tse.RedirectBlock(),
    tse.RequireBlock(),
    tseBlocks.RandomBlock(),
    tseBlocks.ReactBlock(),
    tseBlocks.ReactUBlock(),
    tseBlocks.SilentBlock(),
]
ENGINE = tse.Interpreter(_blocks)


class Group:
    """Dummy class for splitted subcommands group"""

    def __init__(self, command: commands.Group, subcommands: list):
        self.self = command
        self.commands = subcommands


class CCMode(Enum):
    MOD_ONLY = 0
    PARTIAL = 1
    ANARCHY = 2

    def __str__(self):
        MODES = [
            "Only mods can add and manage custom commands",
            "Member can add custom command but can only manage **their own** commands",
            "**A N A R C H Y**",
        ]
        return MODES[self.value]


class CustomCommand:
    """Object for custom command."""

    __slots__ = (
        "id",
        "type",
        "name",
        "invokedName",
        "brief",
        "short_doc",
        "description",
        "help",
        "category",
        "content",
        "aliases",
        "url",
        "uses",
        "owner",
        "enabled",
    )

    def __init__(self, id, name: str, category, **kwargs):
        self.id = id
        # NOTE: Can be 'text' or 'imported'
        # - text: using text and not imported from pastebin/gist
        # - imported: imported from pastebin/gist
        self.type = kwargs.pop("type", "text")
        # Will always return None unless type == 'imported'
        self.url = kwargs.pop("url", None)

        self.name = name
        # Incase its invoked using its alias
        self.invokedName = kwargs.pop("invokedName", name)

        # TODO: Add "brief"
        self.brief = None
        self.short_doc = self.brief
        self.description = kwargs.pop("description", None)
        self.help = self.description
        self.content = kwargs.pop("content", "NULL")
        self.category = category
        self.aliases = kwargs.pop("aliases", [])
        self.uses = kwargs.pop("uses", -1)
        self.owner = kwargs.pop("owner", None)
        enabled = kwargs.pop("enabled", 1)
        self.enabled = True if enabled == 1 else False

    def __str__(self):
        return self.name

    async def canManage(self, context: Context) -> bool:
        guild: discord.Guild | None = context.guild
        if not guild:
            raise CCommandNotInGuild

        mode = await context.bot.getGuildConfig(guild.id, "ccMode") or 0
        isMod = await checks.isMod(context)
        isCmdOwner = context.author.id == self.owner

        return {
            0: isMod,
            1: isCmdOwner or isMod,
            2: True,
        }.get(mode, False)

    def processTag(self, ctx, argument: str | None = None):
        """Process tags from CC's content with TSE."""
        author = tse.MemberAdapter(ctx.author)
        content = self.content
        # TODO: Make target uses custom command arguments instead
        target = tse.MemberAdapter(ctx.message.mentions[0]) if ctx.message.mentions else author
        channel = tse.ChannelAdapter(ctx.channel)
        seed = {
            "author": author,
            "user": author,
            "target": target,
            "member": target,
            "channel": channel,
            "unix": tse.IntAdapter(int(utcnow().timestamp())),
            "prefix": ctx.prefix,
            "uses": tse.IntAdapter(self.uses + 1),
            "argument": argument,
        }
        if ctx.guild:
            guild = tse.GuildAdapter(ctx.guild)
            seed.update(guild=guild, server=guild)
        return ENGINE.process(content, seed)

    async def execute(self, ctx: Context, argument: str | None = None, *, raw: bool = False):
        if not ctx.guild:
            raise CCommandNotInGuild

        if raw:
            content = discord.utils.escape_markdown(self.content)
            return await ctx.try_reply(content)

        # "raw" bypass disable
        if not self.enabled:
            raise CCommandDisabled

        # Increment uses
        await db.Commands.filter(id=self.id).update(uses=self.uses + 1)

        result = self.processTag(ctx)
        embed = result.actions.get("embed")

        dest = result.actions.get("target")
        action = ctx.send
        kwargs = {"reference": ctx.replied_reference}
        if dest:
            if dest == "reply":
                action = ctx.try_reply
                kwargs["reference"] = ctx.replied_reference or ctx.message  # type: ignore
            if dest == "dm":
                action = ctx.author.send
                kwargs = {}

        msg = await action(
            result.body or ("\u200b" if not embed else ""),
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=False),
            **kwargs,
        )
        react = result.actions.get("react")
        reactu = result.actions.get("reactu")
        if reactu:
            ctx.bot.loop.create_task(reactsToMessage(ctx.message, reactu))
        if react:
            ctx.bot.loop.create_task(reactsToMessage(msg, react))

    @classmethod
    async def get(cls, context: Context, command: str | CMDName) -> CustomCommand:
        guild: discord.Guild | None = context.guild
        if not guild:
            raise CCommandNotInGuild

        lookup: db.CommandsLookup | None = await db.CommandsLookup.filter(name=command, guild_id=guild.id).first()
        if not lookup:
            # No command found
            raise CCommandNotFound(command)

        _id = lookup.cmd_id
        name = lookup.name

        results: db.CommandsLookup | None = await db.CommandsLookup.filter(cmd_id=_id).prefetch_related("cmd")
        if not results:
            raise CCommandNotFound(command)

        cmd: db.Commands = results[0].cmd

        return cls(
            id=_id,
            content=cmd.content,
            name=cmd.name,
            invokedName=name,
            description=cmd.description,
            category=cmd.category,
            aliases=[alias.name for alias in results if alias.name != cmd.name],
            uses=cmd.uses,
            url=cmd.url,
            owner=cmd.ownerId,
            enabled=cmd.enabled,
        )

    @staticmethod
    async def getAll(context: Context | discord.Object, category: str = None) -> list[CustomCommand]:
        if isinstance(context, Context):
            guild: discord.Object | (discord.Guild | None) = context.guild
        else:
            guild = context

        if not guild:
            raise CCommandNotInGuild

        cmds = {}

        query = db.CommandsLookup.filter(guild_id=guild.id)
        if category:
            query = query.filter(cmd__category=category.lower())

        lookupRes = await query.prefetch_related("cmd")

        if not lookupRes:
            return []

        # Create temporary dict
        for lookup in lookupRes:
            cmd: db.Commands = lookup.cmd  # type: ignore

            isAlias = lookup.name != cmd.name

            if cmd.id not in cmds:
                cmds[cmd.id] = {}

            if not isAlias:
                # If its not an alias
                cmds[cmd.id] = {
                    "name": cmd.name,  # "real" name
                    "description": cmd.description,
                    "category": cmd.category,
                    "owner": cmd.ownerId,
                    "enabled": cmd.enabled,
                    "uses": cmd.uses,
                }
            else:
                try:
                    cmds[cmd.id]["aliases"] += [lookup.name]
                except KeyError:
                    cmds[cmd.id]["aliases"] = [lookup.name]

        return [CustomCommand(id=k, **v) for k, v in cmds.items()]
