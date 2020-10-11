import asyncio
import bot
import discord
import json
import logging
import re

from bot import get_prefix
from discord.ext import commands
from typing import Optional


class CustomHelp(commands.HelpCommand):
    COLOUR = discord.Colour.blue()

    def get_desc(self):
        prefixes = bot.get_prefix(self.context.bot, self.context.message)
        if len(prefixes) > 1:
            s = "are"
        else:
            s = "is"
        prefixes = ", ".join([f"`{i}`" for i in prefixes])
        prefixes = re.sub(r"`<\S*[0-9]+(..)`", self.context.bot.user.mention, prefixes)
        desc = f"Bot prefixes {s} {prefixes}"
        return desc

    def get_ending_note(self):
        return "Use {0}{1} [command] for more info on a command.".format(
            self.clean_prefix, self.invoked_with
        )

    def get_command_signature(self, cmd):
        return f"{self.cmd_and_alias(cmd)} {cmd.signature}"

    def command_not_found(self, string):
        return f"There's no command called `{string}`"

    def subcommand_not_found(self, command, string):
        if isinstance(command, Group) and len(command.all_commands) > 0:
            return f"Command `{command.qualified_name}` has no subcommand called `{string}`"
        return f"Command `{command.qualified_name}` has no subcommands"

    def cmd_and_alias(self, command):
        cmd = " | ".join([str(command.qualified_name), *command.aliases])
        return cmd

    async def send_error_message(self, error):
        embed = discord.Embed(
            title="Error!", description=f"{error}", colour=discord.Colour(0x2F3136)
        )

        await self.get_destination().send(embed=embed)

    async def send_bot_help(self, mapping):
        destination = self.get_destination()
        embed = discord.Embed(
            title="Bot Commands", description=self.get_desc(), colour=self.COLOUR
        )
        for cog, commands in mapping.items():

            def f(x):
                return {
                    "src": "<:src:757467110564954172>",
                    "moderation": "🔨",
                    "customcommands": "❗",
                    "help": "❓",
                    "utils": "🔧",
                    "anilist": "<:anilist:757473769101983784>",
                    "fun": "🎉",
                    "general": "🗨️",
                }.get(x.lower(), "​")

            name = (
                "No Category"
                if cog is None
                else f"{f(cog.qualified_name)} {cog.qualified_name}".title()
            )
            value = f"```{self.clean_prefix}help {'No Category' if cog is None else cog.qualified_name}```"
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                #     value = ", ".join(f"`{c.name}`" for c in commands)
                #     if cog and cog.description:
                #         value = f"{cog.description}\n{value}"
                if cog.qualified_name.lower() not in ["help", "pingloop"]:
                    embed.add_field(name=name, value=value, inline=True)
        embed.set_footer(text=self.get_ending_note())
        await destination.send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=f"{cog.qualified_name} Commands",
            description=self.get_desc()
            + "\n\
                                 `()` = Required\n\
                                 `[]` = Optional",
            colour=self.COLOUR,
        )
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            if command.brief:
                value = command.brief
            else:
                value = command.short_doc
            embed.add_field(
                name=self.get_command_signature(command),
                value=value or "...",
                inline=False,
            )

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(
            title=group.qualified_name,
            description=self.get_desc()
            + "\n"
            + "`()` = Required\n"
            + "`[]` = Optional",
            colour=self.COLOUR,
        )
        if group.help:
            embed.description = "`()` = Required\n" + "`[]` = Optional\n" + group.help

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                if command.brief:
                    value = command.brief
                else:
                    value = command.short_doc
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=value or "No description.",
                    inline=False,
                )

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=self.clean_prefix+self.get_command_signature(command),
            description=command.help or "No description.",
            colour=self.COLOUR,
        )
        if command.example:
            value = str(command.example).replace("{prefix}", self.clean_prefix)
            embed.add_field(name="Example", value=value)

        await self.get_destination().send(embed=embed)


class Help(commands.Cog, name="Help", command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("discord")
        self._original_help_command = bot.help_command
        bot.help_command = CustomHelp()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    @commands.command(aliases=["customcommands", "ccmds"])
    async def listcommands(self, ctx):
        """List all custom commands."""
        await ctx.invoke(self.bot.get_command("custom list"))
        await ctx.send(
            f"This command will be removed soon, please use `{ctx.prefix}custom list` instead"
        )


def setup(bot):
    bot.add_cog(Help(bot))
