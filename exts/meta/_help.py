from typing import Optional

import discord
from discord.ext import commands

from core.errors import CCommandNotFound, NotInGuild
from core.objects import CustomCommand
from utils import infoQuote
from utils.format import ZEmbed, formatCmd, formatDiscordDT, separateStringFlags

from ._custom_command import getCustomCommand, getCustomCommands
from ._flags import HelpFlags


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
            name="News | Updated at: {}".format(formatDiscordDT(1628066360, "F")),
            value=(
                "Changelogs:"
                "\n- Added Image category"
                "\n- Added cooldown"
                "\n- Changed how help command looks (again)"
                "\n- Added anti-mute evasion"
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

    async def send_cog_help(self, cog):
        ctx = self.context

        # Getting all the commands
        filtered = await self.filter_commands(cog.get_commands())
        if ctx.guild:
            ccs = await getCustomCommands(ctx.db, ctx.guild.id, cog.qualified_name)
            for cmd in ccs:
                filtered.append(cmd)
        filtered = sorted(filtered, key=lambda c: c.name)

        desc = infoQuote.info(
            "` ᶜ ` = Custom Command\n` ᵍ ` = Group (have subcommand(s))",
        )

        e = ZEmbed(
            title=f"{getattr(cog, 'icon', '❓')} | Category: {cog.qualified_name}",
            description=desc,
        )
        for cmd in filtered:
            name = cmd.name
            if isinstance(cmd, CustomCommand):
                name += "ᶜ"
            if isinstance(cmd, commands.Group):
                name += "ᵍ"

            e.add_field(
                name=name,
                value="> " + (cmd.brief or "No description"),
            )
        e.set_footer(
            text="Use `{}command info command-name` to get custom command's information".format(
                ctx.clean_prefix
            )
        )
        await ctx.try_reply(embed=e)

    async def command_not_found(self, type_: str, string):
        return "No {} called `{}` found.".format(type_, string)

    async def send_error_message(self, error):
        if isinstance(error, CustomCommand):
            return
        await self.context.error(error)

    async def send_command_help(self, command):
        ctx = self.context
        prefix = ctx.clean_prefix

        e = ZEmbed(
            title=formatCmd(prefix, command),
            description="**Aliases**: `{}`\n".format(
                ", ".join(command.aliases) if command.aliases else "No alias"
            )
            + (command.description or command.brief or "No description"),
        )

        if isinstance(command, CustomCommand):
            author = ctx.bot.get_user(command.owner) or await ctx.bot.fetch_user(
                command.owner
            )
            e.set_author(name="By {}".format(author), icon_url=author.avatar.url)

        if isinstance(command, (commands.Command, commands.Group)):
            extras = getattr(command, "extras", {})

            optionDict: Optional[dict] = extras.get("flags")
            if optionDict:
                optionStr = []
                for key, value in optionDict.items():
                    name = (
                        " | ".join([f"`{i}`" for i in key])
                        if isinstance(key, tuple)
                        else f"`{key}`"
                    )
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
                        "> {0._cooldown.rate} command per "
                        "{0._cooldown.per} seconds, per {0.type[0]}".format(cooldown)
                    ),
                )
            e.set_footer(
                text="Use `{}command info command-name` to get custom command's information".format(
                    ctx.clean_prefix
                )
            )

        if isinstance(command, commands.Group):
            subcmds = sorted(command.commands, key=lambda c: c.name)  # type: ignore # 'command' already checked as commands.Group
            if subcmds:
                e.add_field(
                    name="Subcommands",
                    value="\n".join(
                        [f"> `{formatCmd(prefix, cmd)}`" for cmd in subcmds]
                    ),
                )

        await ctx.try_reply(embed=e)

    async def prepare_help_command(self, ctx, arguments) -> tuple:
        if arguments is None:
            return None, None, None

        # separate string from flags
        # String filters: String -> ("String", "filters: String")
        command, args = separateStringFlags(arguments)
        await super().prepare_help_command(ctx, command)
        if not command:
            return None, None, None

        # default filters, based on original help cmd
        defFilters = ("category", "built-in", "custom")
        filters = []

        # parse flags is not an empty string
        if args:
            parsed = await HelpFlags.convert(ctx, args)
            for f in parsed.filters:
                filters.extend(f.strip().split())

        # All available filters
        filterAvailable = ("category", "custom", "built-in")
        filterAliases = {
            "cat": "category",
            "C": "category",
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

        return command, args, unique

    async def command_callback(self, ctx, *, arguments=None):
        command, args, filters = await self.prepare_help_command(ctx, arguments)
        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        maybeCoro = discord.utils.maybe_coroutine

        string = None

        type_ = "command/category"

        for filter_ in filters:
            if filter_ == "category":
                # Check if it's a cog
                cog = bot.get_cog(command)
                if cog is None:
                    # type_ = "category"
                    continue
                return await self.send_cog_help(cog)

            if filter_ == "custom":
                try:
                    cc = await getCustomCommand(ctx, command)
                    return await self.send_command_help(cc)
                except CCommandNotFound:
                    # type_ = "command"
                    continue

            # If it's not a cog then it's a command.
            # Since we want to have detailed errors when someone
            # passes an invalid subcommand, we need to walk through
            # the command group chain ourselves.
            keys = command.split(" ")
            cmd = bot.all_commands.get(keys[0])
            if cmd is None:
                # type_ = "command"
                continue

            for key in keys[1:]:
                try:
                    found = cmd.all_commands.get(key)
                except AttributeError:
                    string = await maybeCoro(
                        self.subcommand_not_found, cmd, self.remove_mentions(key)
                    )
                    continue
                else:
                    if found is None:
                        string = await maybeCoro(
                            self.subcommand_not_found, cmd, self.remove_mentions(key)
                        )
                        continue
                    cmd = found

            return await self.send_command_help(cmd)  # works for both Group and Command

        if string is None:
            try:
                cmdName = keys[0]  # type: ignore # handled using except
            except (IndexError, UnboundLocalError):
                cmdName = command
            string = await maybeCoro(
                self.command_not_found, type_, self.remove_mentions(cmdName)
            )

        return await self.send_error_message(string)
