import asyncio
import bot
import discord
import json
import logging

from bot import get_prefix
from discord.ext import commands
from typing import Optional

def syntax(command):
    if not command.usage:
        params = []
        for key, value in command.params.items():
            if key not in ("self", "ctx"):
                params.append(f"[{key}]" if "NoneType" in str(value) else f"<{key}>")

        params = " ".join(params)
        if not params:
            return f"{command}"
        return f"{command} {params}"
    return f"{command} {command.usage}"

class CustomHelp(commands.MinimalHelpCommand):

    COLOUR = discord.Colour.blue()

    def get_ending_note(self):
        return 'Use {0}{1} [command] for more info on a command.'.format(self.clean_prefix, self.invoked_with)

    def get_command_signature(self, command):
        return '{0.qualified_name} {0.signature}'.format(command)

    async def send_bot_help(self, mapping):
        destination = self.get_destination()
        prefixes = get_prefix()
        prefixes = ", ".join(f"`{p}`" for p in prefixes)
        desc = f"Bot prefixes are {prefixes}\n\
                `[]` = Required\n\
                `()` = Optional"
        embed = discord.Embed(title="Bot Commands",
                              description=desc,
                              colour=self.COLOUR)
        for cog, commands in mapping.items():
            name = 'No Category' if cog is None else cog.qualified_name
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                value = ', '.join(f"`{c.name}`" for c in commands)
                if cog and cog.description:
                    value = f'{cog.description}\n{value}'
                
                embed.add_field(name=name, value=value, inline=False)
        await destination.send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title=f'{cog.qualified_name} Commands', colour=self.COLOUR)
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=self.get_command_signature(command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=group.qualified_name, colour=self.COLOUR)
        if group.help:
            embed.description = group.help

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(name=self.get_command_signature(command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)
    
    async def send_command_help(self, command):
        embed = discord.Embed(title=f"Help with {command.qualified_name} command",
                              colour=self.COLOUR)
        if command.help:
            value = command.help
        embed.add_field(name=self.get_command_signature(command), value=value)

        await self.get_destination().send(embed=embed)

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("discord")
        self._original_help_command = bot.help_command
        bot.help_command = CustomHelp()
        bot.help_command.cog = self
        
    def cog_unload(self):
        self.bot.help_command = self._original_help_command
    
    @commands.command(aliases=['customcommands', 'ccmds'])
    async def listcommands(self, ctx):
        """List all custom commands."""
        embed = discord.Embed(
                    title = "Help",
                    colour = discord.Colour.gold()
                )
        with open('custom_commands.json', 'r') as f:
            commands = json.load(f)
            ccmds = ", ".join([*commands])
            # await ctx.send(f"```List of custom commands: \n{ccmds}```")
            # output += f'{ccmds}```'
        embed.add_field(name="Custom Commands", value=f"{ccmds}", inline=False)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Help(bot))

