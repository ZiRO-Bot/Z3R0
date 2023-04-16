"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import discord
from discord.app_commands import locale_str
from discord.ext import commands, menus

from ...core.context import Context
from ...core.embed import Field, ZEmbed, ZEmbedBuilder
from ...core.menus import ZMenuView
from ...utils.format import cleanifyPrefix, formatCmd, info
from ._custom_command import CustomCommand
from ._utils import getDisabledCommands
from ._wrapper import GroupSplitWrapper


class PrefixesPageSource(menus.ListPageSource):
    def __init__(self, ctx, prefixes) -> None:
        self.prefixes = prefixes
        self.ctx = ctx

        super().__init__(prefixes, per_page=6)

    async def format_page(self, menu: ZMenuView, _prefixes: list):
        ctx: Context = self.ctx

        e = ZEmbedBuilder(title=locale_str("prefix-list-title", guildName=ctx.requireGuild().name))

        kwargs = {"defaultPrefix": ctx.bot.defPrefix, "mentionPrefix": cleanifyPrefix(ctx.bot, ctx.me.mention)}

        if menu.currentPage == 0:
            _prefixes.pop(0)
            _prefixes.pop(0)
            e.description = locale_str("prefix-list-desc-default", **kwargs)
        else:
            e.description = locale_str("prefix-list-desc")

        prefixes = []
        for prefix in _prefixes:
            fmt = "• "
            if prefix == "`":
                fmt += "`` {} ``"
            elif prefix == "``":
                fmt += "` {} `"
            else:
                fmt += "`{}`"
            prefixes.append(fmt.format(cleanifyPrefix(ctx.bot, prefix)))
        if not prefixes:
            e.description = locale_str("prefix-list-desc-empty", **kwargs)
        e.description = await ctx.translate(e.description) + "\n".join(prefixes)
        return await e.build(ctx)


class HelpCogPage(menus.ListPageSource):
    def __init__(self, cog: commands.Cog, commands):
        self.cog = cog
        self.disabled = None
        super().__init__(commands, per_page=6)

    async def format_page(self, menu: ZMenuView, _commands):
        ctx: Context = menu.context
        cog = self.cog

        if ctx.guild and self.disabled is None:
            self.disabled = await getDisabledCommands(ctx.bot, ctx.guild.id)
        elif not ctx.guild:
            self.disabled = []

        desc = info(await ctx.translate(locale_str("help-cog-info")))

        e = ZEmbedBuilder(
            title=locale_str(
                "help-cog-title",
                icon=getattr(cog, 'icon', '❓'),
                category=cog.qualified_name,
            ),
            description=desc,
        )

        if not _commands:
            e.description = str(e.description) + await ctx.translate(locale_str("help-cog-no-command"))
            return await e.build(ctx)

        for cmd in _commands:
            name = cmd.name
            if isinstance(cmd, CustomCommand):
                if not cmd.enabled:
                    name = f"~~{name}~~"
                name += "ᶜ"
            else:
                if cmd.name in self.disabled:
                    name = f"~~{name}~~"

            if isinstance(cmd, (commands.HybridCommand, commands.HybridGroup)):
                name += "ˢ"

            if isinstance(cmd, commands.Group):
                name += "ᵍ"

            e.addField(name=name, value="> " + await ctx.maybeTranslate(cmd.description, "No description"), inline=True)
        return await e.build(ctx)


class HelpCommandPage(menus.ListPageSource):
    def __init__(self, commands) -> None:
        super().__init__(commands, per_page=1)

    async def format_page(self, menu: ZMenuView, command) -> discord.Embed:
        ctx: Context = menu.context
        prefix = ctx.clean_prefix

        subcmds = None
        if isinstance(command, GroupSplitWrapper):
            subcmds = command.commands
            command = command.origin

        description: locale_str | str = command.description or locale_str("no-description")
        if isinstance(description, locale_str):
            description = await ctx.translate(description)
        description += await ctx.maybeTranslate(command.help, "")

        aliases: str = (
            ", ".join(command.aliases) if command.aliases else await ctx.translate(locale_str("help-command-no-alias"))
        )
        e = ZEmbedBuilder(
            title=formatCmd(prefix, command),
            description=locale_str("help-command-desc", aliases=aliases, description=description),
        )

        if isinstance(command, (commands.HybridCommand, commands.HybridGroup)):
            e.title = str(e.title).strip() + "ˢ"

        if isinstance(command, CustomCommand):
            e.title = str(e.title).strip() + "ᶜ"
            e.addField(
                name=locale_str("help-command-cc-info-title"),
                value=locale_str(
                    "help-command-cc-info", ownerMention=str(command.owner), uses=command.uses, enabled=command.enabled
                ),
            )
            e.addField(
                name=locale_str("help-command-cc-tips-title"),
                value=locale_str("help-command-cc-tips", prefix=prefix),
            )

        if isinstance(command, (commands.Command, commands.Group)):
            extras = getattr(command, "extras", {})

            optionDict: Optional[dict] = extras.get("flags")
            if optionDict:
                optionStr = []
                for key, value in optionDict.items():
                    name = " | ".join([f"`{i}`" for i in key]) if isinstance(key, tuple) else f"`{key}`"
                    optionStr.append(f"> {name}: {value}")
                e.addField(name=locale_str("help-command-options-title"), value="\n".join(optionStr))

            examples = extras.get("example")
            if examples:
                e.addField(
                    name=locale_str("help-command-example-title"),
                    value="\n".join([f"> `{prefix}{x}`" for x in examples]),
                )

            perms = extras.get("perms", {})
            botPerm = perms.get("bot")
            userPerm = perms.get("user")
            if botPerm is not None or userPerm is not None:
                e.addField(
                    name=locale_str("help-command-perms-title"),
                    value=locale_str("help-command-perms", botPerms=botPerm, userPerms=userPerm),
                )

            cooldown = command._buckets  # type: ignore
            if cooldown._cooldown:
                e.addField(
                    name=locale_str("help-command-cooldown-title"),
                    value=locale_str(
                        "help-command-cooldown",
                        rate=cooldown._cooldown.rate,
                        per=cooldown._cooldown.per,
                        type=str(cooldown.type[0]),  # type: ignore
                    ),
                    inline=True,
                )

        if subcmds:
            e.addField(
                name=locale_str("help-command-subcommands-title"),
                value="\n".join([f"> `{formatCmd(prefix, cmd)}`" for cmd in subcmds]),
                inline=True,
            )
        return await e.build(ctx)


class CustomCommandsListSource(menus.ListPageSource):
    def __init__(self, list_: List[Tuple[int, CustomCommand]]) -> None:
        super().__init__(list_, per_page=6)

    def format_page(self, menu: ZMenuView, list_: List[Tuple[int, CustomCommand]]) -> ZEmbed:
        ctx = menu.context
        e = ZEmbed(
            title=f"Custom Commands in {ctx.guild}",
            fields=[
                Field(
                    f"**`{count+1}`** {command} (**`{command.uses}`** uses)",
                    command.description or "No description",
                )
                for count, command in list_
            ],
            fieldInline=False,
        )
        return e
