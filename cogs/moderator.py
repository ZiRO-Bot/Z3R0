import asyncio
import datetime
import discord
import git
import json
import logging
import os
import time

from bot import get_cogs
from discord.errors import Forbidden
from discord.ext import commands
from utilities.formatting import realtime

class Admin(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('discord')
        self.bot = bot
    
    async def is_mod(ctx):
        return ctx.author.guild_permissions.manage_channels

    async def is_botmaster(ctx):
        return ctx.author.id in [ 186713080841895936, 366219142799556620 ]

    @commands.command(aliases=['quit'], hidden=True)
    @commands.check(is_botmaster)
    async def force_close(self, ctx):
        """Shutdown the bot."""
        await ctx.send("Shutting down...")
        await ctx.bot.logout()
    
    @commands.command(hidden=True)
    @commands.check(is_mod)
    async def unload(self, ctx, ext):
        """Unload an extension."""
        await ctx.send(f"Unloading {ext}...")
        try:
            self.bot.unload_extension(f'cogs.{ext}')
            await ctx.send(f"{ext} has been unloaded.")
        except commands.ExtensionNotFound:
            await ctx.send(f"{ext} doesn't exist!")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{ext} is not loaded!")
        except commands.ExtensionFailed:
            await ctx.send(f"{ext} failed to unload! Check the log for details.")
            self.bot.logger.exception(f'Failed to reload extension {ext}:')

    @commands.command(hidden=True)
    @commands.check(is_mod)
    async def reload(self, ctx, ext: str=None):
        """Reload an extension."""
        if not ext:
            reload_start=time.time()
            exts = get_cogs()
            reloaded = []
            error = 0
            for ext in exts:
                try:
                    self.bot.reload_extension(f'{ext}')
                    reloaded.append(f'<:check_mark:747274119426605116>| {ext}')
                except commands.ExtensionNotFound:
                    reloaded.append(f'<:check_mark:747271588474388522>| {ext}')
                    error += 1
                except commands.ExtensionNotLoaded:
                    reloaded.append(f'<:cross_mark:747274119275479042>| {ext}')
                    error += 1
                except commands.ExtensionFailed:
                    self.bot.logger.exception(f'Failed to reload extension {ext}:')
                    reloaded.append(f'<:cross_mark:747274119275479042>| {ext}')
                    error += 1
            reloaded = "\n".join(reloaded)
            embed = discord.Embed(
                                  title="Reloading all cogs...",
                                  description=f"{reloaded}",
                                  colour=discord.Colour(0x2F3136)
                                 )
            embed.set_footer(text=f"{len(exts)} cogs has been reloaded" 
                                   + f", with {error} errors \n"
                                   + f"in {realtime(time.time() - reload_start)}")
            await ctx.send(embed=embed)
            return
        await ctx.send(f"Reloading {ext}...")
        try:
            self.bot.reload_extension(f'cogs.{ext}')
            await ctx.send(f"{ext} has been reloaded.")
        except commands.ExtensionNotFound:
            await ctx.send(f"{ext} doesn't exist!")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{ext} is not loaded!")
        except commands.ExtensionFailed:
            await ctx.send(f"{ext} failed to reload! Check the log for details.")
            self.bot.logger.exception(f'Failed to reload extension {ext}:')

    @commands.command(hidden=True)
    @commands.check(is_mod)
    async def load(self, ctx, ext):
        """Load an extension."""
        await ctx.send(f"Loading {ext}...")
        try:
            self.bot.load_extension(f"cogs.{ext}")
            await ctx.send(f"{ext} has been loaded.")
        except commands.ExtensionNotFound:
            await ctx.send(f"{ext} doesn't exist!")
        except commands.ExtensionFailed:
            await ctx.send(f"{ext} failed to load! Check the log for details.")
            self.bot.logger.exception(f'Failed to reload extension {ext}:')

    @commands.command(aliases=['cc'], hidden=True)
    @commands.check(is_mod)
    async def clearchat(self, ctx, numb: int=100):
        """Clear the chat."""
        deleted_msg = await ctx.message.channel.purge(limit=int(numb)+1, check=None, before=None, after=None, around=None, oldest_first=False, bulk=True)

        msg_num = max(len(deleted_msg) - 1, 0)

        if msg_num == 0:
            resp = "Deleted `0 message` 😔 "
            # resp = "Deleted `0 message` 🙄  \n (I can't delete messages "\
                      # "older than 2 weeks due to discord limitations)"
        else:
            resp = "Deleted `{} message{}` ✨ ".format(msg_num,
                                                         "" if msg_num <\
                                                            2 else "s")

        await ctx.send(resp)
    
    @commands.command(hidden=True)
    @commands.check(is_mod)
    async def mute(self, ctx, member: discord.Member=None, reason: str="No Reason", min_muted: int=0):
        """Mute a member."""
        if member is None:
            await ctx.send("Please specify the member you want to mute.")
            return
        muted_role = discord.utils.get(member.guild.roles, name="Muted")
        if self.bot.user == member: # Just why would you want to mute him?
            await ctx.send(f'You\'re not allowed to mute ziBot!')
        else:
            if muted_role in member.roles:
                await ctx.send(f'{member.mention} is already muted.')
            else:
                await member.add_roles(muted_role)
                await ctx.send(f'{member.mention} has been muted by {ctx.author.mention} for {reason}!')

        if min_muted > 0:
            await asyncio.sleep(min_muted * 60)
            await member.remove_roles(muted_role)

    @commands.command(hidden=True)
    @commands.check(is_mod)
    async def unmute(self, ctx, member: discord.Member=None):
        """Unmute a member."""
        if member is None:
            await ctx.send("Please specify the member you want to unmute.")
            return
        muted_role = discord.utils.get(member.guild.roles, name="Muted")
        if muted_role in member.roles:
            await member.remove_roles(muted_role)
            await ctx.send(f'{member.mention} has been unmuted by {ctx.author.mention}.')
        else:
            await ctx.send(f'{member.mention} is not muted.')

    @commands.command(hidden=True)
    @commands.check(is_mod)
    async def kick(self, ctx, member: discord.Member=None, reason: str="No Reason"): 
        """Kick a member."""
        if member is None:
            await ctx.send("Please specify the member you want to kick.")
            return
        if self.bot.user == member: # Just why would you want to mute him?
            await ctx.send(f'You\'re not allowed to kick ziBot!')
        else:
            try:
                await member.send(f'You have been kicked from {ctx.guild.name} for {reason}!')
            except discord.errors.HTTPException:
                pass
            await ctx.guild.kick(member, reason=reason)
            await ctx.send(f'{member.mention} has been kicked by {ctx.author.mention} for {reason}!')
    
    @commands.command(hidden=True)
    @commands.check(is_mod)
    async def ban(self, ctx, member: discord.Member=None, reason: str="No Reason", min_ban: int=0): 
        """Ban a member."""
        if member is None:
            await ctx.send("Please specify the member you want to ban.")
            return
        if self.bot.user == member: # Just why would you want to mute him?
            await ctx.send(f'You\'re not allowed to ban ziBot!')
        else:
            await member.send(f'You have been banned from {ctx.guild.name} for {reason}!')
            await ctx.guild.ban(member, reason=reason)
            await ctx.send(f'{member.mention} has been banned by {ctx.author.mention} for {reason}!')
        
        if min_ban > 0:
            await asyncio.sleep(min_ban * 60)
            await ctx.guild.unban(member, reason="timed out")
    
    @commands.command(hidden=True)
    @commands.check(is_mod)
    async def unban(self, ctx, member):
        """Unban a member."""
        for s in "<!@>":
            member = member.replace(s,"")
        member = await self.bot.fetch_user(int(member))
        if member is None:
            await ctx.send("Please specify the member you want to unban.")
            return
        try:
            await member.send(f'You have been unbanned from {ctx.guild.name}!')
        except Forbidden:
            self.logger.error("discord.errors.Forbidden: Can't send DM to member")
        await ctx.guild.unban(member)
        await ctx.send(f'{member.mention} has been unbanned by {ctx.author.mention}!')
    
    @commands.command(hidden=True)
    @commands.check(is_botmaster)
    async def pull(self, ctx):
        """Update the bot from github."""
        g = git.cmd.Git(os.getcwd())
        embed = discord.Embed(
                title = "Git",
                colour = discord.Colour.lighter_gray(),
                timestamp = datetime.datetime.now()
                )
        try:
            embed.add_field(name="Pulling...", value=f"```bash\n{g.pull()}```")
        except git.exc.GitCommandError as e:
            embed.add_field(name="Pulling...", value=f"```bash\n{e}```")
        await ctx.send(embed=embed)

    @commands.command(aliases=['addcommand', 'newcommand'])
    @commands.check(is_mod)
    async def setcommand(self, ctx, command, *, message):
        """Add a new simple command"""
        self.bot.custom_commands[ctx.prefix + command] = message
        with open('data/custom_commands.json', 'w') as f:
            json.dump(self.bot.custom_commands, f, indent=4)

        await ctx.send(f"Set message for command {command}")

    @commands.command(aliases=['deletecommand'])
    @commands.check(is_mod)
    async def removecommand(self, ctx, command):
        """Remove a simple command"""
        del self.bot.custom_commands[ctx.prefix + command]
        with open('data/custom_commands.json', 'w') as f:
            json.dump(self.bot.custom_commands, f, indent=4)

        await ctx.send(f"Removed command {command}")

def setup(bot):
    bot.add_cog(Admin(bot))
