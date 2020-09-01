import asyncio
import bot
import discord
import json
import logging

from bot import get_prefix
from discord.ext import commands
from typing import Optional

class CustomHelp(commands.MinimalHelpCommand):
    COLOUR = discord.Colour.blue()
    prefixes = get_prefix()
    prefixes = ", ".join(f"`{p}`" for p in prefixes)
    desc = f"Bot prefixes are {prefixes}"

    def get_ending_note(self):
        return 'Use {0}{1} [command] for more info on a command.'.format(self.clean_prefix, self.invoked_with)

    def get_command_signature(self, command):
        return '{0.qualified_name} {0.signature}'.format(command)
    
    def command_not_found(self, string):
        return f'There\'s no command called `{string}`'
    
    def subcommand_not_found(self, command, string):
        if isinstance(command, Group) and len(command.all_commands) > 0:
            return f'Command `{command.qualified_name}` has no subcommand called `{string}`'
        return f'Command `{command.qualified_name}` has no subcommands'

    async def send_error_message(self, error):
        embed = discord.Embed(title="Error!",
                              description=f"{error}",
                              colour=discord.Colour(0x2F3136))

        await self.get_destination().send(embed=embed)
    
    async def send_bot_help(self, mapping):
        destination = self.get_destination()
        embed = discord.Embed(title="Bot Commands",
                              description=self.desc,
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
        embed = discord.Embed(title=f'{cog.qualified_name} Commands',
                              description=self.desc
                              + "\n\
                                 `()` = Required\n\
                                 `[]` = Optional",
                              colour=self.COLOUR)
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            if command.brief:
                value = command.brief
            else:
                value = command.short_doc
            embed.add_field(name=self.get_command_signature(command), value=value or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=group.qualified_name, 
                              description=self.desc
                              + "\n\
                                 `()` = Required\n\
                                 `[]` = Optional",
                              colour=self.COLOUR)
        if group.help:
            embed.description = group.help + "\n\
                                 `()` = Required\n\
                                 `[]` = Optional"

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                if command.brief:
                    value = command.brief
                else:
                    value = command.short_doc
                embed.add_field(name=self.get_command_signature(command), value=value or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)
    
    async def send_command_help(self, command):
        embed = discord.Embed(title=f"Help with {command.qualified_name} command",
                              description=self.desc
                              + "\n\
                                 `()` = Required\n\
                                 `[]` = Optional",
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
        with open('data/custom_commands.json', 'r') as f:
            commands = json.load(f)
            ccmds = ", ".join([*commands])
            # await ctx.send(f"```List of custom commands: \n{ccmds}```")
            # output += f'{ccmds}```'
        embed.add_field(name="Custom Commands", value=f"{ccmds}", inline=False)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Help(bot))

