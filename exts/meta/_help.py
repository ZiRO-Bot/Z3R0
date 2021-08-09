from contextlib import suppress

import discord
from discord.ext import commands

from core.embed import ZEmbed
from core.errors import CCommandNotFound, NotInGuild
from core.menus import ZMenuPagesView
from utils import infoQuote
from utils.format import formatDiscordDT

from ._custom_command import getCustomCommand, getCustomCommands
from ._flags import HelpFlags
from ._objects import CustomCommand, Group
from ._pages import HelpCogPage, HelpCommandPage


class CustomHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context

        e = ZEmbed(
            description=infoQuote.info(
                (
                    "`( )` = Required Argument\n"
                    "`[ ]` = Optional Argument\n"
                    "` / ` = Choices\n"
                    "**NOTE**: Don't literally type `[ ]`, `( )` or ` / ` when using a command!"
                ),
            )
            + " | ".join("[{}]({})".format(k, v) for k, v in ctx.bot.links.items()),
        )
        e.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        e.set_footer(
            text="Use `{}help [category / command]` for more information".format(
                ctx.prefix
            )
        )

        # unsorted = mapping.pop(None)
        mapping.pop(None)
        sortedCog = sorted(mapping.keys(), key=lambda c: c.qualified_name)

        ignored = ("EventHandler", "Jishaku", "NSFW")
        e.add_field(
            name="Categories",
            value="\n".join(
                [
                    "`⦘` {} **{}**".format(
                        getattr(cog, "icon", "❓"), cog.qualified_name
                    )
                    for cog in sortedCog
                    if cog.qualified_name not in ignored
                ]
            ),
        )
        # TODO: Make a command to set this without reloading the extension
        e.add_field(
            name="News | Updated at: {}".format(formatDiscordDT(1628505078, "F")),
            value=(
                "Changelogs:"
                "\n- Updated `discord.py` to v2.0"
                "\n- Buttons!"
                "\n- Improved help command behaviour"
                "\n- Added AniList category (Anime ~~and Manga~~ commands)"
                "\n- Fixed some issues"
                "\n\n[Click here to see the full changelog!]"
                "(https://github.com/ZiRO-Bot/Z3R0/blob/overhaul/CHANGELOG.md)\n"
            ),
        )

        return await ctx.try_reply(embed=e)

    async def filter_commands(self, _commands):
        async def predicate(cmd):
            try:
                return await cmd.can_run(self.context)
            except (commands.CommandError, NotInGuild):
                return False

        ret = []
        for cmd in _commands:
            if cmd.hidden:
                continue
            valid = await predicate(cmd)
            if valid:
                ret.append(cmd)

        return ret

    async def send_cog_help(self, cog, filters):
        ctx = self.context

        filtered = []
        # Getting all the commands
        for f in filters:
            if f == "built-in":
                builtIns = sorted(
                    await self.filter_commands(cog.get_commands()),
                    key=lambda cmd: cmd.name,
                )
                filtered.extend(builtIns)

            if f == "custom":
                if ctx.guild:
                    ccs = await getCustomCommands(
                        ctx.db, ctx.guild.id, cog.qualified_name
                    )
                    for cmd in ccs:
                        filtered.append(cmd)

        view = ZMenuPagesView(ctx, source=HelpCogPage(cog, filtered))
        await view.start()

    async def command_not_found(self, string):
        return "No command/category called `{}` found.".format(string)

    async def send_error_message(self, error):
        if isinstance(error, CustomCommand):
            return
        await self.context.error(error)

    async def send_command_help(self, commands_):
        ctx = self.context

        filtered = []
        for command in commands_:
            if isinstance(command, commands.Group):
                list_ = list(command.commands)
                perList = 5
                res = [list_[i : i + perList] for i in range(0, len(list_), perList)]
                filtered.extend([Group(command, i) for i in res])
            else:
                filtered.append(command)

        view = ZMenuPagesView(ctx, source=HelpCommandPage(filtered))
        await view.start()

    async def prepare_help_command(self, ctx, arguments) -> tuple:
        if arguments is None:
            return None, None

        # separate string from flags
        # String filters: String -> ("String", "filters: String")
        command, parsed = await HelpFlags.convert(ctx, arguments)
        await super().prepare_help_command(ctx, command)

        # default filters, based on original help cmd
        defFilters = ("built-in", "custom")

        filters = []
        for f in parsed.filters:
            filters.extend(f.strip().split())

        # All available filters
        filterAvailable = ("custom", "built-in")
        filterAliases = {
            "c": "custom",
            "b": "built-in",
        }

        # get unique value from filters (also get "real value" if its an alias)
        unique = []
        for f in filters:
            f = filterAliases.get(f.strip(), f)
            if f in filterAvailable and f not in unique:
                unique.append(f)

        if not unique:
            unique = defFilters

        # if not command and len(unique) == 1:
        # TODO: get command list if no command specified and 1 filters specified
        # This will merge `>command list`
        # return None, None, unique
        # pass

        return command, unique

    async def command_callback(self, ctx, *, arguments=None):
        command, filters = await self.prepare_help_command(ctx, arguments)

        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        cog = bot.get_cog(command)
        if cog:
            return await self.send_cog_help(cog, filters)

        maybeCoro = discord.utils.maybe_coroutine

        # contains custom commands and built-in commands
        foundList = []
        with suppress(CCommandNotFound):
            cc = await getCustomCommand(ctx, command)
            foundList.append(cc)

        keys = command.split(" ")
        cmd = bot.all_commands.get(keys[0])
        if cmd:
            for key in keys[1:]:
                with suppress(AttributeError):
                    found = cmd.all_commands.get(key)
                    if found:
                        cmd = found
            foundList.append(cmd)

        if not foundList:
            string = await maybeCoro(
                self.command_not_found, self.remove_mentions(command)
            )
            return await self.send_error_message(string)

        await self.send_command_help(foundList)
