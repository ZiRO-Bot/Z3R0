import asyncio
import datetime
import discord
import git
import json
import logging
import os
import re
import subprocess
import sys
import time

from bot import get_cogs, get_prefix
from discord.errors import Forbidden
from discord.ext import commands
from utilities.formatting import realtime

SHELL = os.getenv("SHELL") or "/bin/bash"
WINDOWS = sys.platform == "win32"

ch_types = {
        "general": "general",
        "voice": "voice",
        "welcome": "welcome_ch",
        "purgatory": "purge_ch",
        "meme": "meme_ch",
        "pingme": "pingme_ch"
        }

class Admin(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('discord')
        self.bot = bot
    
    def is_mod():
        def predicate(ctx):
            return ctx.author.guild_permissions.manage_channels
        return commands.check(predicate)

    def is_botmaster():
        def predicate(ctx):
            return ctx.author.id in ctx.bot.master
        return commands.check(predicate)

    @commands.command(aliases=['quit'], hidden=True)
    @is_botmaster()
    async def force_close(self, ctx):
        """Shutdown the bot."""
        await ctx.send("Shutting down...")
        await ctx.bot.logout()
    
    @commands.command(usage="(extension)", hidden=True)
    @is_botmaster()
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

    @commands.command(usage="[extension]", hidden=True)
    @is_botmaster()
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

    @commands.command(usage="(extension)", hidden=True)
    @is_botmaster()
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

    @commands.command(aliases=['cc'], usage="[amount of chat]", hidden=True)
    @is_mod()
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
    
    @commands.command(usage="(user) [reason] [mute duration]", hidden=True)
    @is_mod()
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

    @commands.command(usage="(user) [reason]", hidden=True)
    @is_mod()
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

    @commands.command(usage="(user) [reason]", hidden=True)
    @is_mod()
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
    
    @commands.command(usage="(user) [reason] [ban duration]", hidden=True)
    @is_mod()
    async def ban(self, ctx, member: discord.User=None, reason: str="No Reason", min_ban: int=0): 
        """Ban a member."""
        if member is None:
            await ctx.send("Please specify the member you want to ban.")
            return
        if self.bot.user == member: # Just why would you want to mute him?
            await ctx.send(f'You\'re not allowed to ban ziBot!')
        else:
            try:
                await member.send(f'You have been banned from {ctx.guild.name} for {reason}!')
            except Forbidden:
                self.logger.error("discord.errors.Forbidden: Can't send DM to member")
            await ctx.guild.ban(member, reason=reason)
            await ctx.send(f'{member.mention} has been banned by {ctx.author.mention} for {reason}!')
        
        if min_ban > 0:
            await asyncio.sleep(min_ban * 60)
            await ctx.guild.unban(member, reason="timed out")
    
    @commands.command(usage="(user) [reason]", hidden=True)
    @is_mod()
    async def unban(self, ctx, member: discord.User=None):
        """Unban a member."""
        # for s in "<!@>":
        #     member = member.replace(s,"")
        # member = await self.bot.fetch_user(int(member))
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
    @is_botmaster()
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

    @commands.command(aliases=['addcommand', 'newcommand'], usage="(command name) (command messages)")
    @commands.check_any(is_mod(), is_botmaster())
    async def setcommand(self, ctx, command, *, message):
        """Add a new simple command."""
        self.bot.custom_commands[str(ctx.guild.id)][ctx.prefix + command] = message
        with open('data/custom_commands.json', 'w') as f:
            json.dump(self.bot.custom_commands, f, indent=4)
        embed = discord.Embed(
                              title="New command has been added!",
                              description=f"{ctx.prefix}{command}"
                             )
        await ctx.send(embed=embed)

    @commands.command(aliases=['deletecommand'], usage="(command name)")
    @commands.check_any(is_mod(), is_botmaster())
    async def removecommand(self, ctx, command):
        """Remove a simple command."""
        del self.bot.custom_commands[str(ctx.guild.id)][ctx.prefix + command]
        with open('data/custom_commands.json', 'w') as f:
            json.dump(self.bot.custom_commands, f, indent=4)
        embed = discord.Embed(
                              title="A command has been removed!",
                              description=f"{ctx.prefix}{command}"
                             )
        await ctx.send(embed=embed)

    @commands.group()
    async def prefix(self, ctx):
        """Manage bot's prefix."""
        pass

    @prefix.command()
    async def list(self, ctx):
        """List bot's prefixes."""
        prefix = self.bot.config[str(ctx.guild.id)]['prefix']
        if len(prefix) > 1:
            s="es are"
        else:
            s=" is"
        await ctx.send(f"My prefix{s} `{', '.join(prefix)}`")
    
    @prefix.command(name="mention")
    @commands.check_any(is_mod(), is_botmaster())
    async def togglemention(self, ctx):
        """Toggle mention as prefix."""
        g = ctx.message.guild
        with open('data/guild.json', 'w') as f:
            if self.bot.config[str(g.id)]['mention_as_prefix'] is True:
                self.bot.config[str(g.id)]['mention_as_prefix'] = False
                s = "Deactivated"
            elif self.bot.config[str(g.id)]['mention_as_prefix'] is False:
                self.bot.config[str(g.id)]['mention_as_prefix'] = True
                s = "Activated"
            else:
                json.dump(self.bot.config, f, indent=4)
                return
            json.dump(self.bot.config, f, indent=4)
        embed = discord.Embed(
                              title=f"Mention as prefix has been `{s}`"
                             )
        await ctx.send(embed=embed)
    
    @prefix.command(name="set", usage="(prefix)")
    @commands.check_any(is_mod(), is_botmaster())
    async def prefixset(self, ctx, *, prefix):
        """Change bot's prefix."""
        g = ctx.message.guild
        prefix = [*prefix]
        prefix.append(" ")
        prefixes = []
        tmp = ""
        i = 0
        for _prefix in prefix:
            if _prefix != " ":
                i = 0
                tmp+=str(_prefix)
            else:
                i += 1
                if i == 2:
                    pass
                else:
                    prefixes.append(tmp)
                    tmp=""
        with open('data/guild.json', 'w') as f:
            self.bot.config[str(g.id)]['prefix'] = prefixes
            json.dump(self.bot.config, f, indent=4)
        embed = discord.Embed(
                              title=f"Prefix has been changed to `{', '.join(prefixes)}`"
                             )
        await ctx.send(embed=embed)

    @commands.command(usage="(variable) (value)")
    @is_botmaster()
    async def setvar(self, ctx, key, *, value):
        """Set a config variable, ***use with caution!**"""
        with open('data/guild.json', 'w') as f:
            if value[0] == '[' and value[len(value) - 1] == ']':
                value = list(map(int, value[1:-1].split(',')))
            try:
                value = int(value)
            except ValueError:
                pass
            self.bot.config[str(ctx.message.guild.id)][key] = value
            json.dump(self.bot.config, f, indent=4)

    @commands.command(usage="[variable]")
    @commands.check_any(is_mod(), is_botmaster())
    async def printvar(self, ctx, key=None):
        """Print config variables, use for testing."""
        if key == None:
            for key, value in self.bot.config[str(
                    ctx.message.guild.id)].items():
                await ctx.send(f'Key: {key} | Value: {value}')
        else:
            await ctx.send(self.bot.config[str(ctx.message.guild.id)][key])

    @commands.command(aliases=['rmvar'], usage="(variable)")
    @is_botmaster()
    async def delvar(self, ctx, key):
        """Deletes a config variable, be careful!"""
        with open('data/guild.json', 'w') as f:
            await ctx.send(
                    f"Removed {self.bot.config[str(ctx.message.guild.id)].pop(key)}"
                    )
            json.dump(self.bot.config, f, indent=4)

    @commands.command()
    @is_botmaster()
    async def leave(self, ctx):
        """Leave the server."""
        await ctx.message.guild.leave()

    @commands.group()
    @is_mod()
    async def channel(self, ctx):
        """Manage server's channel."""
        pass

    @channel.command(alias=['type'])
    async def types(self, ctx):
        """Get channel types."""
        _type = ", ".join(list(ch_types.keys()))
        await ctx.send(f"Channel types: `{_type}`")

    @channel.command(aliases=["make"], brief="Create a new channel.", usage="(channel type) (channel name)")
    async def create(self, ctx, _type, *name):
        """Create a new channel."""
        if not _type:
            return
        name = "-".join([*name])
        if not name:
            return
        g = ctx.message.guild
        if _type.lower() == "voice":
            ch = await g.create_voice_channel(name)
            e = discord.Embed(title=f"Voice Channel called `{name}` has been created!")
        else:
            if _type.lower() not in list(ch_types.keys()):
                await ctx.send("Not valid channel type")
                return
            ch = await g.create_text_channel(name)
            if _type.lower() == "general":
                e = discord.Embed(title=f"Text Channel called `{ch.name}` has been created!")
            else:
                with open('data/guild.json', 'w') as f:

                    key = ch_types[_type.lower()]

                    try:
                        value = int(ch.id)
                    except ValueError:
                        json.dump(self.bot.config, f, indent=4)
                        return

                    self.bot.config[str(ctx.message.guild.id)][key] = value
                    json.dump(self.bot.config, f, indent=4)
                e = discord.Embed(title=f"Text Channel for {_type.title()} " 
                                      + f"called `{ch.name}` has been created!")
                
        await ctx.send(embed=e)
    
    @channel.command(name="set", usage="(channel id) (channel type)")
    async def ch_set(self, ctx, _id, _type):
        """Change channel type."""
        # Check if _id is int
        try:
            _id = int(_id)
        except ValueError:
            await ctx.send(f"Only numbers is allowed!\n**Example**: `{ctx.prefix}channel set 746649217543700551 general`")
            return

        if _type.lower() not in list(ch_types.keys()):
            await ctx.send("Not valid channel type")
            return
        elif _type.lower() in ['general', 'voice']:
            await ctx.send(f"You can't set channels to `{_type}`")
            return

        ch = ctx.guild.get_channel(_id)
        # Test if channel with the following id exist
        try:
            ch.name
        except AttributeError:
            await ctx.send(f"There's no channel with id `{_id}`")
            return
        
        # Check if channel is a VoiceChannel
        if isinstance(ch, discord.channel.VoiceChannel):
            await ctx.send("You cannot change Voice Channel's type!")
            return

        # If all good do the thing
        with open('data/guild.json', 'w') as f:

            key = ch_types[_type.lower()]
            value = _id

            self.bot.config[str(ctx.message.guild.id)][key] = value
            json.dump(self.bot.config, f, indent=4)
        e = discord.Embed(title=f"``{ch.name}``'s type has been changed to ``{_type}``")
        await ctx.send(embed=e)
    
    @commands.command(aliases=['sh'], usage="(shell command)", hidden=True)
    @is_botmaster()
    async def shell(self, ctx, *command: str):
        """Execute shell command from discord. **Use with caution**"""
        if WINDOWS:
            sequence = shlex.split(' '.join([*command]))
        else:
            sequence = [SHELL, '-c', ' '.join([*command])]

        proc = subprocess.Popen(sequence, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        def clean_bytes(line):
            """
            Cleans a byte sequence of shell directives and decodes it.
            """
            lines = line
            line = []
            for i in lines:
                line.append(i.decode('utf-8'))
            line = "".join(line)
            text = line.replace('\r', '').strip('\n')
            return re.sub(r'\x1b[^m]*m', '', text).replace("``", "`\u200b`").strip('\n')
        await ctx.send(f"```{clean_bytes(proc.stdout.readlines())}```")

def setup(bot):
    bot.add_cog(Admin(bot))
