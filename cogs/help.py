from typing import Optional
from discord.ext import commands
import discord
import asyncio
import json
import bot
import logging

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("discord")

    @commands.command(aliases=["commands", "cmds"])
    async def help(self, ctx, command: Optional[str]):
        """Show this message."""
        _prefixes_ = bot.get_prefix(self.bot, ctx.message)
        _prefixes_.pop(0)
        _prefixes_.pop(0)
        prefixes = ", ".join(_prefixes_)
        embed = discord.Embed(
                    title = "Help",
                    # description = f"* Bot prefixes are {prefixes} *",
                    description = f"*` Bot prefixes are {prefixes} `*",
                    colour = discord.Colour.green()
                )
        if command is None:
            cmds = list(self.bot.commands)
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
        await ctx.send("help <command> is not available yet")

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

