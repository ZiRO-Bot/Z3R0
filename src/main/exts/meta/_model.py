from enum import Enum

from discord.ext import commands

from ...core import checks
from ...core.context import Context


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

    def __init__(self, id, name, category, **kwargs):
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
        mode = await context.bot.getGuildConfig(context.guild.id, "ccMode") or 0
        isMod = await checks.isMod(context)
        isCmdOwner = context.author.id == self.owner

        return {
            0: isMod,
            1: isCmdOwner or isMod,
            2: True,
        }.get(mode, False)
