import asyncio
import bot
import copy
import datetime
import discord
import git
import json
import logging
import os
import re
import subprocess
import sys
import textwrap
import time

from bot import get_cogs, get_prefix
from cogs.utilities.embed_formatting import em_ctx_send_error
from discord.errors import Forbidden, NotFound
from discord.ext import commands
from typing import Optional
from utilities.formatting import realtime

SHELL = os.getenv("SHELL") or "/bin/bash"
WINDOWS = sys.platform == "win32"

ch_types = {
    "general": ["general", "Regular text channel"],
    "voice": ["voice", "Voice channel"],
    "greeting": ["greeting_ch", "Text channel for welcome/farewell messages"],
    "purgatory": ["purge_ch", "Text channel for monitoring edited/deleted messages"],
    "meme": ["meme_ch", "Text channel for meme commands"],
    "anime": ["anime_ch", "Text channel for anime releases"],
    "pingme": ["pingme_ch", "Text channel to get ping by pingme command"],
    "announcement": [
        "announcement_ch",
        "Text channel for announcements (for announce command)",
    ],
}

role_types = {
    "general": ["general", "Regular role"],
    "default": ["default_role", "Default role, will be given when the member join"],
    "mute": ["mute_role", "Make a member can't send messages"],
}


async def copy_context_with(
    ctx: commands.Context, *, author=None, channel=None, **kwargs
):
    """
    Makes a new :class:`Context` with changed message properties.
    """

    # copy the message and update the attributes
    alt_message: discord.Message = copy.copy(ctx.message)
    alt_message._update(kwargs)  # pylint: disable=protected-access

    if author is not None:
        alt_message.author = author
    if channel is not None:
        alt_message.channel = channel

    # obtain and return a context of the same type
    return await ctx.bot.get_context(alt_message, cls=type(ctx))


class Admin(commands.Cog, name="moderation"):
    def __init__(self, bot):
        self.logger = logging.getLogger("discord")
        self.bot = bot

    def is_mod():
        def predicate(ctx):
            return ctx.author.guild_permissions.manage_channels

        return commands.check(predicate)

    def is_botmaster():
        def predicate(ctx):
            return ctx.author.id in ctx.bot.master

        return commands.check(predicate)

    @commands.command(aliases=["quit"], hidden=True)
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
            self.bot.unload_extension(f"cogs.{ext}")
            await ctx.send(f"{ext} has been unloaded.")
        except commands.ExtensionNotFound:
            await ctx.send(f"{ext} doesn't exist!")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{ext} is not loaded!")
        except commands.ExtensionFailed:
            await ctx.send(f"{ext} failed to unload! Check the log for details.")
            self.bot.logger.exception(f"Failed to reload extension {ext}:")

    @commands.command(usage="[extension]", hidden=True)
    @is_botmaster()
    async def reload(self, ctx, ext: str = None):
        """Reload an extension."""
        if not ext:
            reload_start = time.time()
            exts = get_cogs()
            reloaded = []
            error = 0
            for ext in exts:
                try:
                    self.bot.reload_extension(f"{ext}")
                    reloaded.append(f"<:check_mark:747274119426605116>| {ext}")
                except commands.ExtensionNotFound:
                    reloaded.append(f"<:check_mark:747271588474388522>| {ext}")
                    error += 1
                except commands.ExtensionNotLoaded:
                    reloaded.append(f"<:cross_mark:747274119275479042>| {ext}")
                    error += 1
                except commands.ExtensionFailed:
                    self.bot.logger.exception(f"Failed to reload extension {ext}:")
                    reloaded.append(f"<:cross_mark:747274119275479042>| {ext}")
                    error += 1
            reloaded = "\n".join(reloaded)
            embed = discord.Embed(
                title="Reloading all cogs...",
                description=f"{reloaded}",
                colour=discord.Colour(0x2F3136),
            )
            embed.set_footer(
                text=f"{len(exts)} cogs has been reloaded"
                + f", with {error} errors \n"
                + f"in {realtime(time.time() - reload_start)}"
            )
            await ctx.send(embed=embed)
            return
        await ctx.send(f"Reloading {ext}...")
        try:
            self.bot.reload_extension(f"cogs.{ext}")
            await ctx.send(f"{ext} has been reloaded.")
        except commands.ExtensionNotFound:
            await ctx.send(f"{ext} doesn't exist!")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{ext} is not loaded!")
        except commands.ExtensionFailed:
            await ctx.send(f"{ext} failed to reload! Check the log for details.")
            self.bot.logger.exception(f"Failed to reload extension {ext}:")

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
            self.bot.logger.exception(f"Failed to reload extension {ext}:")

    @commands.command(aliases=["cc"], usage="[amount of chat]", hidden=True)
    @is_mod()
    async def clearchat(self, ctx, numb: int = 100):
        """Clear the chat."""
        deleted_msg = await ctx.message.channel.purge(
            limit=int(numb) + 1,
            check=None,
            before=None,
            after=None,
            around=None,
            oldest_first=False,
            bulk=True,
        )

        msg_num = max(len(deleted_msg) - 1, 0)

        if msg_num == 0:
            resp = "Deleted `0 message` 😔 "
            # resp = "Deleted `0 message` 🙄  \n (I can't delete messages "\
            # "older than 2 weeks due to discord limitations)"
        else:
            resp = "Deleted `{} message{}` ✨ ".format(
                msg_num, "" if msg_num < 2 else "s"
            )

        await ctx.send(resp)

    @commands.command(usage="(member) [reason];[duration]", hidden=True)
    @is_mod()
    async def mute(
        self,
        ctx,
        members: commands.Greedy[discord.Member],
        *,
        reason_duration: str = "No Reason;0",
    ):
        """Mute members."""

        # split reason and duration
        r_and_d = reason_duration.split(";")
        if len(r_and_d) < 2:
            r_and_d.append("0")
        reason = r_and_d[0]
        min_muted = int(r_and_d[1])

        if not members:
            return await ctx.send("Please specify the member you want to mute.")

        self.bot.c.execute(
            "SELECT mute_role FROM roles WHERE id=?", (str(ctx.guild.id),)
        )
        muted_role = self.bot.c.fetchall()[0][0]
        if not muted_role:
            await ctx.send(
                "This server does not have a mute role, "
                + f"use `{ctx.prefix}role set mute (role name)` to"
                + f" set one or `{ctx.prefix}role create mute (role name)` to create one."
            )
            return
        muted_role = ctx.guild.get_role(int(muted_role))

        # mute multiple member
        for member in members:
            if self.bot.user == member:  # Just why would you want to mute him?
                await ctx.send(f"You're not allowed to mute ziBot!")
            else:
                if muted_role in member.roles:
                    await ctx.send(f"{member.mention} is already muted.")
                else:
                    await member.add_roles(muted_role)
                    duration = ""
                    if min_muted > 0:
                        duration = f" ({min_muted} minutes)"
                    await ctx.send(
                        f"{member.mention} has been muted by {ctx.author.mention} for {reason}!{duration}"
                    )

            if min_muted > 0:
                await asyncio.sleep(min_muted * 60)
                await member.remove_roles(muted_role)

    @commands.command(usage="(member)", hidden=True)
    @is_mod()
    async def unmute(self, ctx, members: commands.Greedy[discord.Member]):
        """Unmute members."""
        if not members:
            return await ctx.send("Please specify the member you want to unmute.")

        self.bot.c.execute(
            "SELECT mute_role FROM roles WHERE id=?", (str(ctx.guild.id),)
        )
        muted_role = self.bot.c.fetchall()[0][0]
        if not muted_role:
            await ctx.send(
                "This server does not have a mute role, "
                + f"use `{ctx.prefix}role set mute (role name)` to"
                + f" set one or `{ctx.prefix}role create mute (role name)` to create one."
            )
            return
        muted_role = ctx.guild.get_role(int(muted_role))

        for member in members:
            if muted_role in member.roles:
                await member.remove_roles(muted_role)
                await ctx.send(
                    f"{member.mention} has been unmuted by {ctx.author.mention}."
                )
            else:
                await ctx.send(f"{member.mention} is not muted.")

    @commands.command(usage="(member) [reason]", hidden=True)
    @is_mod()
    async def kick(
        self, ctx, members: commands.Greedy[discord.Member], *, reason: str = "No Reason"
    ):
        """Kick a member."""
        if not members:
            return await ctx.send("Please specify the member you want to kick.")
        
        for member in members:
            if self.bot.user == member:  # Just why would you want to mute him?
                await ctx.send(f"You're not allowed to kick ziBot!")
            else:
                try:
                    await member.send(
                        f"You have been kicked from {ctx.guild.name} for {reason}!"
                    )
                except discord.errors.HTTPException:
                    pass
                await ctx.guild.kick(member, reason=reason)
                await ctx.send(
                    f"{member.mention} has been kicked by {ctx.author.mention} for {reason}!"
                )

    @commands.command(usage="(user) [ban duration] [reason]", hidden=True)
    @is_mod()
    async def ban(
        self,
        ctx,
        members: commands.Greedy[discord.User],
        *,
        reason_duration: str = "No Reason;0",
    ):
        """Ban a member."""
        r_and_d = reason_duration.split(";")
        if len(r_and_d) < 2:
            r_and_d.append("0")
        reason = r_and_d[0]
        min_ban = int(r_and_d[1])
        
        if not members:
            return await ctx.send("Please specify the member you want to ban.")
            
        for member in members:
            if self.bot.user == member:  # Just why would you want to mute him?
                await ctx.send(f"You're not allowed to ban ziBot!")
            else:
                try:
                    await member.send(
                        f"You have been banned from {ctx.guild.name} for {reason}!"
                    )
                except Forbidden:
                    self.logger.error("discord.errors.Forbidden: Can't send DM to member")
                await ctx.guild.ban(member, reason=reason, delete_message_days=0)
                duration = ""
                if min_muted > 0:
                    duration = f" ({min_ban} minutes)"
                await ctx.send(
                    f"{member.mention} has been banned by {ctx.author.mention} for {reason}!{duration}"
                )
    
            if min_ban > 0:
                await asyncio.sleep(min_ban * 60)
                await ctx.guild.unban(member, reason="timed out")

    @commands.command(usage="(user)", hidden=True)
    @is_mod()
    async def unban(self, ctx, members: commands.Greedy[discord.User]):
        """Unban a member."""
        if not members:
            return await ctx.send("Please specify the member you want to unban.")
        
        for member in members:
            # try:
            #     await member.send(f"You have been unbanned from {ctx.guild.name}!")
            # except Forbidden:
            #     self.logger.error("discord.errors.Forbidden: Can't send DM to member")
            # except AttributeError:
            #     self.logger.error("Attribute error!")
            try:
                await ctx.guild.unban(member)
            except NotFound:
                await ctx.send(f"{member.mention} is not banned!")
                continue
            await ctx.send(f"{member.mention} has been unbanned by {ctx.author.mention}!")

    @commands.command(hidden=True)
    @is_botmaster()
    async def pull(self, ctx):
        """Update the bot from github."""
        g = git.cmd.Git(os.getcwd())
        embed = discord.Embed(
            title="Git",
            colour=discord.Colour.lighter_gray(),
            timestamp=datetime.datetime.now(),
        )
        try:
            embed.add_field(name="Pulling...", value=f"```bash\n{g.pull()}```")
        except git.exc.GitCommandError as e:
            embed.add_field(name="Pulling...", value=f"```bash\n{e}```")
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx):
        """Manage bot's prefix."""
        await ctx.invoke(self.bot.get_command("prefix list"))
        pass

    @prefix.command(name="list")
    async def prefix_list(self, ctx):
        """List bot's prefixes."""
        prefix = bot.get_prefix(self.bot, ctx.message)
        if self.bot.user.mention in prefix:
            prefix.pop(0)
        prefixes = ", ".join([f"`{i}`" for i in prefix])
        prefixes = re.sub(r"`<\S*[0-9]+(..)`", self.bot.user.mention, prefixes)
        if len(prefix) > 1:
            s = "es are"
        else:
            s = " is"
        await ctx.send(f"My prefix{s} {prefixes}")

    @prefix.command(name="add", usage="(prefix)")
    @commands.check_any(is_mod(), is_botmaster())
    async def prefixadd(self, ctx, *prefixes):
        """Add a new prefix to bot."""
        g = ctx.guild
        added = []
        prefixes = list([*prefixes])
        ori_prefixes = list(bot.get_prefix(self.bot, ctx.message))
        # Filter whitespaces and prefix that already exist from *prefixes
        for prefix in prefixes:
            match = re.match(r"^\s+", prefix)
            if match or prefix in ori_prefixes or prefix == ",":
                prefixes.remove(prefix)
            else:
                added.append(prefix)
        prefixes = ori_prefixes + prefixes
        if len(prefixes) > 15:
            await em_ctx_send_error(ctx, "You can only add up to 15 prefixes!")
            return
        # database stuff
        up_prefixes = ",".join(sorted([*prefixes]))
        self.bot.c.execute(
            "UPDATE servers SET prefixes = ? WHERE id = ?",
            (up_prefixes, str(ctx.guild.id)),
        )
        self.bot.conn.commit()
        # inform the user
        if len(added) > 0:
            await ctx.send(f"`{', '.join(added)}` successfully added to prefix")
            return
        await ctx.send("No prefix successfully added")

    @prefix.command(name="remove", aliases=["rm"], usage="(prefix)")
    @commands.check_any(is_mod(), is_botmaster())
    async def prefixrm(self, ctx, *prefixes):
        """Remove a prefix from bot."""
        g = ctx.guild
        removed = []
        ori_prefixes = list(bot.get_prefix(self.bot, ctx.message))
        for prefix in prefixes:
            if prefix in ori_prefixes and len(ori_prefixes) - 1 >= 1:
                removed.append(prefix)
                ori_prefixes.remove(prefix)
            else:
                pass
        # database stuff
        up_prefixes = ",".join(sorted(ori_prefixes))
        self.bot.c.execute(
            "UPDATE servers SET prefixes = ? WHERE id = ?",
            (up_prefixes, str(ctx.guild.id)),
        )
        self.bot.conn.commit()
        # inform the user
        if len(removed) > 0:
            await ctx.send(f"`{', '.join(removed)}` successfully removed from prefix")
            return
        await ctx.send("No prefix successfully removed")

    # @commands.command(usage="(variable) (value)")
    # @is_botmaster()
    # async def setvar(self, ctx, key, *, value):
    #     """Set a config variable, ***use with caution!**"""
    #     with open("data/guild.json", "w") as f:
    #         if value[0] == "[" and value[len(value) - 1] == "]":
    #             value = list(map(int, value[1:-1].split(",")))
    #         try:
    #             value = int(value)
    #         except ValueError:
    #             pass
    #         self.bot.config[str(ctx.message.guild.id)][key] = value
    #         json.dump(self.bot.config, f, indent=4)

    # @commands.command(usage="[variable]")
    # @commands.check_any(is_mod(), is_botmaster())
    # async def printvar(self, ctx, key=None):
    #     """Print config variables, use for testing."""
    #     if key == None:
    #         for key, value in self.bot.config[str(ctx.message.guild.id)].items():
    #             await ctx.send(f"Key: {key} | Value: {value}")
    #     else:
    #         await ctx.send(self.bot.config[str(ctx.message.guild.id)][key])

    # @commands.command(aliases=["rmvar"], usage="(variable)")
    # @is_botmaster()
    # async def delvar(self, ctx, key):
    #     """Deletes a config variable, be careful!"""
    #     with open("data/guild.json", "w") as f:
    #         await ctx.send(
    #             f"Removed {self.bot.config[str(ctx.message.guild.id)].pop(key)}"
    #         )
    #         json.dump(self.bot.config, f, indent=4)

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

    @channel.command(alias=["type"])
    async def types(self, ctx):
        """Get channel types."""
        e = discord.Embed(title="Channel Types")
        for _type in ch_types:
            e.add_field(name=_type, value=ch_types[_type][1], inline=False)
        await ctx.send(embed=e)

    @channel.command(
        aliases=["+", "make"],
        brief="Create a new channel.",
        usage="(channel type) (channel name)",
    )
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
                e = discord.Embed(
                    title=f"Text Channel called `{ch.name}` has been created!"
                )
            else:
                key = ch_types[_type.lower()][0]
                value = ch.id

                self.bot.c.execute(
                    f"UPDATE servers SET {key} = ? WHERE id = ?",
                    (int(value), str(g.id)),
                )
                self.bot.conn.commit()

                e = discord.Embed(
                    title=f"Text Channel for {_type.title()} "
                    + f"called `{ch.name}` has been created!"
                )

        await ctx.send(embed=e)

    @channel.command(name="set", usage="(channel type) (channel)")
    async def ch_set(self, ctx, _type, ch: discord.TextChannel = None):
        """Change channel type."""
        # Check if _id is int
        # try:
        #     _id = int(_id)
        # except ValueError:
        #     await ctx.send(
        #         f"Only numbers is allowed!\n**Example**: `{ctx.prefix}channel set 746649217543700551 general`"
        #     )
        #     return

        if _type.lower() not in list(ch_types.keys()):
            await ctx.send("Not valid channel type")
            return
        elif _type.lower() in ["general", "voice"]:
            await em_ctx_send_error(ctx, f"You can't set channels to `{_type}`")
            return

        key = ch_types[_type.lower()][0]
        value = ch.id

        self.bot.c.execute(
            f"UPDATE servers SET {key} = ? WHERE id = ?",
            (int(value), str(ctx.guild.id)),
        )
        self.bot.conn.commit()

        e = discord.Embed(title=f"``{ch.name}``'s type has been changed to ``{_type}``")
        await ctx.send(embed=e)

    @ch_set.error
    async def ch_set_handler(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            match = re.match(r"Channel \"[0-9]*\" not found.", str(error))
            if match:
                await em_ctx_send_error(ctx, "You can only set a text channel's type!")

    @commands.command(aliases=["sh"], usage="(shell command)", hidden=True)
    @is_botmaster()
    async def shell(self, ctx, *command: str):
        """Execute shell command from discord. **Use with caution**"""
        if WINDOWS:
            sequence = shlex.split(" ".join([*command]))
        else:
            sequence = [SHELL, "-c", " ".join([*command])]

        proc = subprocess.Popen(sequence, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        def clean_bytes(line):
            """
            Cleans a byte sequence of shell directives and decodes it.
            """
            lines = line
            line = []
            for i in lines:
                line.append(i.decode("utf-8"))
            line = "".join(line)
            text = line.replace("\r", "").strip("\n")
            return re.sub(r"\x1b[^m]*m", "", text).replace("``", "`\u200b`").strip("\n")

        await ctx.send(f"```{clean_bytes(proc.stdout.readlines())}```")

    @commands.command(usage="(command)")
    @is_botmaster()
    async def sudo(self, ctx: commands.Context, *, command_string: str):
        """
        Run a command bypassing all checks and cooldowns.
        """

        alt_ctx = await copy_context_with(ctx, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        return await alt_ctx.command.reinvoke(alt_ctx)

    @commands.group()
    @commands.check_any(is_mod(), is_botmaster())
    async def role(self, ctx):
        """Manage server's roles."""
        pass

    @role.command(name="types", aliases=["type"])
    async def role_types(self, ctx):
        """Get channel types."""
        e = discord.Embed(title="Role Types")
        for _type in role_types:
            e.add_field(name=_type, value=role_types[_type][1], inline=False)
        await ctx.send(embed=e)

    @role.command(name="set", usage="(type) (role)")
    async def role_set(self, ctx, role_type, role: discord.Role):
        """Set type for a role"""
        if role_type.lower() in role_types:
            if role_type.lower() != "general":

                key = role_types[role_type.lower()][0]
                value = int(role.id)

                self.bot.c.execute(
                    f"UPDATE roles SET {key} = ? WHERE id = ?",
                    (int(value), str(ctx.guild.id)),
                )
                self.bot.conn.commit()

                e = discord.Embed(
                    title=f"`{role.name}`'s type has been changed to {role_type.lower()}!"
                )
                await ctx.send(embed=e)

    @role.command(aliases=["+", "create"], usage="(type) (role name)")
    async def make(self, ctx, role_type, *role_name):
        """Make a new role."""
        name = " ".join([*role_name])
        if not name:
            return
        g = ctx.guild
        if role_type.lower() in role_types:
            role = await g.create_role(name=name)
            if role_type.lower() != "general":
                key = role_types[role_type.lower()][0]
                value = int(role.id)

                self.bot.c.execute(
                    f"UPDATE roles SET {key} = ? WHERE id = ?", (int(value), str(g.id))
                )
                self.bot.conn.commit()

                e = discord.Embed(
                    title=f"Role for `{role_type}` "
                    + f"called `{role.name}` has been created!"
                )
            else:
                e = discord.Embed(
                    title=f"Role for called `{role.name}` has been created!"
                )
            await ctx.send(embed=e)

    @commands.group(aliases=["emote", "emo"])
    async def emoji(self, ctx):
        """Managed server's emoji."""
        pass

    @emoji.command(name="list")
    async def emoji_list(self, ctx):
        """List all emoji in the server."""
        emojis = " ".join([str(emoji) for emoji in ctx.guild.emojis])
        emoji_list = textwrap.wrap(emojis, 1024)

        page = 1
        total_page = len(emoji_list)
        embed_reactions = ["◀️", "▶️", "⏹️"]

        def check_reactions(reaction, user):
            if user == ctx.author and str(reaction.emoji) in embed_reactions:
                return str(reaction.emoji)
            else:
                return False

        def create_embed(ctx, page):
            e = discord.Embed(
                title="Emojis",
                description=emoji_list[page - 1],
                color=discord.Colour(0xFFFFF0),
                timestamp=ctx.message.created_at,
            )
            e.set_author(
                name=f"{ctx.guild.name} - {page}/{total_page}",
                icon_url=ctx.guild.icon_url,
            )
            e.set_footer(
                text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
            )
            return e

        embed = create_embed(ctx, page)
        msg = await ctx.send(embed=embed)
        for emoji in embed_reactions:
            await msg.add_reaction(emoji)
        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=check_reactions, timeout=60.0
                )
            except asyncio.TimeoutError:
                break
            else:
                emoji = check_reactions(reaction, user)
                try:
                    await msg.remove_reaction(reaction.emoji, user)
                except discord.Forbidden:
                    pass
                if emoji == "◀️" and page != 1:
                    page -= 1
                    embed = create_embed(ctx, page)
                    await msg.edit(embed=embed)
                if emoji == "▶️" and page != total_page:
                    page += 1
                    embed = create_embed(ctx, page)
                    await msg.edit(embed=embed)
                if emoji == "⏹️":
                    # await msg.clear_reactions()
                    break
        return

    @emoji.command(name="add", aliases=["+"], usage="(name)")
    @is_mod()
    async def emoji_add(self, ctx, name: Optional[str], emote_pic: Optional[str]):
        """Add emoji to a server."""
        if ctx.message.attachments and not emote_pic:
            for attachment in ctx.message.attachments:
                emote_pic = await attachment.read()
        if not emote_pic:
            await ctx.send("You need to attach an image of the emoji!")
            return
        if not name:
            await ctx.send("You need to specify a name for the emoji!")
            return
        if len(name) < 2:
            await ctx.send(
                "The name of the emoji needs to be at least 2 characters long!"
            )
            return
        try:
            added_emote = await ctx.guild.create_custom_emoji(
                name=name, image=emote_pic
            )
        except Forbidden:
            await ctx.send("Bot need **Manage Emojis** permission for this command!")
            return
        embed = discord.Embed(
            title="New emote has been added!",
            description=f"{str(added_emote)} `:{added_emote.name}:`",
            color=discord.Colour(0xFFFFF0),
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(
            text=f"Added by {ctx.message.author.name}#{ctx.message.author.discriminator}"
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Admin(bot))
