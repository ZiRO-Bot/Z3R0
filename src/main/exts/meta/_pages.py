"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Any, List, Optional, Tuple

from discord.ext import commands, menus

from ...core.embed import ZEmbed
from ...core.menus import ZMenuView
from ...utils import infoQuote
from ...utils.format import cleanifyPrefix, formatCmd
from ._custom_command import CustomCommand
from ._model import Group
from ._utils import getDisabledCommands


class PrefixesPageSource(menus.ListPageSource):
    def __init__(self, ctx, prefixes) -> None:
        self.prefixes = prefixes
        self.ctx = ctx

        super().__init__(prefixes, per_page=6)

    async def format_page(self, menu: ZMenuView, _prefixes: list):
        ctx = self.ctx

        e = ZEmbed(title="{} Prefixes".format(ctx.guild), description="**Custom Prefixes**:\n")

        if menu.currentPage == 0:
            _prefixes.pop(0)
            _prefixes.pop(0)
            e.description = "**Default Prefixes**: `{}` or `{} `\n\n**Custom Prefixes**:\n".format(
                ctx.bot.defPrefix, cleanifyPrefix(ctx.bot, ctx.me.mention)
            )

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
        e.description += "\n".join(prefixes) or "No custom prefix."
        return e


class HelpCogPage(menus.ListPageSource):
    def __init__(self, cog: commands.Cog, commands):
        self.cog = cog
        self.disabled = None
        super().__init__(commands, per_page=6)

    async def format_page(self, menu: ZMenuView, _commands):
        ctx = menu.context
        cog = self.cog

        if ctx.guild and self.disabled is None:
            self.disabled = await getDisabledCommands(ctx.bot, ctx.guild.id)
        elif not ctx.guild:
            self.disabled = []

        desc = infoQuote.info(
            "` ᶜ ` = Custom Command\n" "` ᵍ ` = Group (have subcommand(s))\n" "~~` C `~~ = Disabled",
        )

        e = ZEmbed(
            title=f"{getattr(cog, 'icon', '❓')} | Category: {cog.qualified_name}",
            description=desc,
        )

        if not _commands:
            e.description += "\nNo usable commands."
            return e

        for cmd in _commands:
            name = cmd.name
            if isinstance(cmd, CustomCommand):
                if not cmd.enabled:
                    name = f"~~{name}~~"
                name += "ᶜ"
            else:
                if cmd.name in self.disabled:
                    name = f"~~{name}~~"
            if isinstance(cmd, commands.Group):
                name += "ᵍ"

            e.add_field(
                name=name,
                value="> " + (cmd.short_doc or "No description"),
            )
        return e


class HelpCommandPage(menus.ListPageSource):
    def __init__(self, commands) -> None:
        super().__init__(commands, per_page=1)

    async def format_page(self, menu: ZMenuView, command):
        ctx = menu.context
        prefix = ctx.clean_prefix

        subcmds = None
        if isinstance(command, Group):
            subcmds = command.commands
            command = command.self

        e = ZEmbed(
            title=formatCmd(prefix, command),
            description="**Aliases**: `{}`\n".format(", ".join(command.aliases) if command.aliases else "No alias")
            + (getattr(command, "help", command.description) or command.short_doc or "No description"),
        )

        if isinstance(command, CustomCommand):
            e.title = e.title.strip() + "ᶜ"
            e.add_field(
                name="Info/Stats",
                value=("**Owner**: <@{0.owner}>\n" "**Uses**: `{0.uses}`\n" "**Enabled**: `{0.enabled}`".format(command)),
            )
            e.set_footer(
                text=(
                    "Add extra `>` or `!` after prefix to prioritize custom "
                    "command.\nExample: `{0}>example` or `{0}!example`".format(prefix)
                )
            )

        if isinstance(command, (commands.Command, commands.Group)):
            extras = getattr(command, "extras", {})

            optionDict: Optional[dict] = extras.get("flags")
            if optionDict:
                optionStr = []
                for key, value in optionDict.items():
                    name = " | ".join([f"`{i}`" for i in key]) if isinstance(key, tuple) else f"`{key}`"
                    optionStr.append(f"> {name}: {value}")
                e.add_field(name="Options", value="\n".join(optionStr), inline=False)

            examples = extras.get("example")
            if examples:
                e.add_field(
                    name="Example",
                    value="\n".join([f"> `{prefix}{x}`" for x in examples]),
                    inline=False,
                )

            perms = extras.get("perms", {})
            botPerm = perms.get("bot")
            userPerm = perms.get("user")
            if botPerm is not None or userPerm is not None:
                e.add_field(
                    name="Required Permissions",
                    value="> Bot: `{}`\n> User: `{}`".format(botPerm, userPerm),
                    inline=False,
                )

            cooldown = command._buckets  # type: ignore
            if cooldown._cooldown:
                e.add_field(
                    name="Cooldown",
                    value=(
                        "> {0._cooldown.rate} command per " "{0._cooldown.per} seconds, per {0.type[0]}".format(cooldown)
                    ),
                )

        if subcmds:
            e.add_field(
                name="Subcommands",
                value="\n".join([f"> `{formatCmd(prefix, cmd)}`" for cmd in subcmds]),
            )
        return e


class CustomCommandsListSource(menus.ListPageSource):
    def __init__(self, list_: List[Tuple[int, CustomCommand]]) -> None:
        super().__init__(list_, per_page=6)

    def format_page(self, menu: ZMenuView, list_: List[Tuple[int, CustomCommand]]) -> ZEmbed:
        ctx = menu.context
        e = ZEmbed(
            title=f"Custom Commands in {ctx.guild}",
            fields=[
                (
                    f"**`{count+1}`** {command} (**`{command.uses}`** uses)",
                    command.description or "No description",
                )
                for count, command in list_
            ],
            field_inline=False,
        )
        return e
