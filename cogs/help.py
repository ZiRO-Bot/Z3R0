from typing import Optional
from discord.ext import commands
import discord
import asyncio
import json
import bot
import logging

def syntax(command):
    params = []
    for key, value in command.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "NoneType" in str(value) else f"<{key}>")

    params = " ".join(params)

    return f"{command} {params}"


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("discord")

    @commands.command(aliases=["commands", "cmds"])
    async def help(self, ctx, command: Optional[str]):
        """Show this message."""
        hidden_cogs = ["Help", "Admin", "Welcome"]
        if command is None:
            _prefixes_ = bot.get_prefix(self.bot, ctx.message)
            _prefixes_.pop(0)
            _prefixes_.pop(0)
            prefixes = ", ".join(_prefixes_)
            embed = discord.Embed(
                    title = "Help",
                    # description = f"* Bot prefixes are {prefixes} *",
                    description = f"*Bot prefixes are {prefixes}*",
                    colour = discord.Colour.green()
                    )
            # cmds = list(self.bot.commands)
            # for cmd in cmds:
            #     if cmd.hidden is True:
            #         continue
            #     if cmd.help is None:
            #         _desc="No description."
            #     else:
            #         _desc=f"{cmd.help}"
            #     _cmd = " | ".join([str(cmd),*cmd.aliases])
            #     embed.add_field(name=f"{_cmd}", value=f"{_desc}", inline=False)
            # await ctx.send(embed=embed)
            for cog in self.bot.cogs:
                if cog in hidden_cogs:
                    continue
                cmds = self.bot.get_cog(cog).get_commands()
                _cmds = ", ".join([c.name for c in cmds])
                if not _cmds:
                    _cmds = "No commands"
                embed.add_field(name=f"{cog}", value=f"` help {cog} for details. ` \n{_cmds}", inline=False)
            await ctx.send(embed=embed)
            return
        if command in self.bot.cogs and command not in hidden_cogs:
            _prefixes_ = bot.get_prefix(self.bot, ctx.message)
            _prefixes_.pop(0)
            _prefixes_.pop(0)
            prefixes = ", ".join(_prefixes_)
            embed = discord.Embed(
                    title = f"Help with {command} commands",
                    description = f"*Bot prefixes are {prefixes}*",
                    colour = discord.Colour.green()
                    )
            cmds = self.bot.get_cog(command).get_commands()
            for cmd in cmds:
                if cmd.hidden is True:
                    continue
                if cmd.help is None:
                    _desc="No description."
                else:
                    _desc=f"{cmd.help}"
                _cmd = " | ".join([str(cmd),*cmd.aliases])
                embed.add_field(name=f"{_cmd}", value=f"{_desc}", inline=False)
            await ctx.send(embed=embed)
            return
        if (command := discord.utils.get(self.bot.commands, name=command)):
            embed = discord.Embed(
                    title = f"Help with {command}",
                    description = f"` {syntax(command)} `",
                    colour = discord.Colour.green()
                    )
            embed.add_field(name="Command Description", value=command.help)
            await ctx.send(embed=embed)
            return
        await ctx.send(f"That command does not exist!" +
                " (Note: help command doesn't work with command aliases)")

    @commands.command(aliases=['customcommands', 'ccmds'])
    async def listcommands(self, ctx):
        """List all custom commands"""
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

