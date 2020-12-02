import asyncio
import core.bot as bot
import cogs.utils.checks as checks
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

from .utils.embed_formatting import em_ctx_send_error, em_ctx_send_success
from .utils.formatting import realtime
from core.bot import get_cogs, _callable_prefix
from discord.errors import Forbidden, NotFound
from discord.ext import commands
from typing import Optional

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


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("discord")
        self.bot = bot

    def get_disabled(self, ctx):
        self.bot.c.execute(
            "SELECT disabled_cmds FROM settings WHERE (id=?)", (str(ctx.guild.id),)
        )
        disabled = self.bot.c.fetchone()
        try:
            disabled_cmds = disabled[0].split(",")
        except AttributeError:
            disabled_cmds = []

        return disabled_cmds

    def get_mods_only(self, ctx):
        self.bot.c.execute(
            "SELECT mods_only FROM settings WHERE (id=?)", (str(ctx.guild.id),)
        )
        mods = self.bot.c.fetchone()
        try:
            mods_only = mods[0].split(",")
        except AttributeError:
            mods_only = []

        return mods_only

    def is_botmaster():
        def predicate(ctx):
            return ctx.author.id in ctx.bot.master

        return commands.check(predicate)

    @commands.command(aliases=["cc"], usage="(amount of chat)", hidden=True)
    @checks.mod_or_permissions(manage_messages=True)
    @checks.is_mod()
    async def clearchat(self, ctx, numb):
        """Clear the chat."""
        try:
            numb = int(numb)
        except ValueError:
            return await ctx.send(f"{numb} is not a valid number!")

        try:
            deleted_msg = await ctx.message.channel.purge(
                limit=numb + 1,
                check=None,
                before=None,
                after=None,
                around=None,
                oldest_first=False,
                bulk=True,
            )
        except Forbidden:
            return await ctx.reply("The bot doesn't have `Manage Messages` permission!")

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
    @checks.is_mod()
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
        reason = r_and_d[0] or "No Reason"
        try:
            min_muted = int(r_and_d[1])
        except ValueError:
            await ctx.send(
                f"**WARNING**: {r_and_d[1]} is not a valid number, value `0` is used instead."
            )
            min_muted = 0

        if not members:
            return await ctx.send(
                f"Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            )

        self.bot.c.execute(
            "SELECT mute_role FROM roles WHERE id=?", (str(ctx.guild.id),)
        )
        muted_role = ctx.guild.get_role(int(self.bot.c.fetchone()[0] or 0))
        if not muted_role:
            await ctx.send(
                "This server does not have a mute role, "
                + f"use `{ctx.prefix}role set mute (role name)` to"
                + f" set one or `{ctx.prefix}role create mute (role name)` to create one."
            )
            return

        # mute multiple member
        for member in members:
            if self.bot.user == member:  # Just why would you want to mute him?
                await ctx.send(f"You're not allowed to mute ziBot!")
            else:
                if muted_role in member.roles:
                    await ctx.send(f"{member.mention} is already muted.")
                else:
                    try:
                        await member.add_roles(muted_role)
                    except Forbidden:
                        return await ctx.send(
                            "I need `Manage Role` permission to mute a member!"
                        )
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
    @checks.is_mod()
    async def unmute(self, ctx, members: commands.Greedy[discord.Member]):
        """Unmute members."""
        if not members:
            return await ctx.send(
                f"Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            )

        self.bot.c.execute(
            "SELECT mute_role FROM roles WHERE id=?", (str(ctx.guild.id),)
        )
        muted_role = ctx.guild.get_role(int(self.bot.c.fetchone()[0] or 0))
        if not muted_role:
            await ctx.send(
                "This server does not have a mute role, "
                + f"use `{ctx.prefix}role set mute (role name)` to"
                + f" set one or `{ctx.prefix}role create mute (role name)` to create one."
            )
            return

        for member in members:
            if muted_role in member.roles:
                await member.remove_roles(muted_role)
                await ctx.send(
                    f"{member.mention} has been unmuted by {ctx.author.mention}."
                )
            else:
                await ctx.send(f"{member.mention} is not muted.")

    @commands.command(usage="(member) [reason]", hidden=True)
    @checks.is_mod()
    async def kick(
        self,
        ctx,
        members: commands.Greedy[discord.Member],
        *,
        reason: str = "No Reason",
    ):
        """Kick a member."""
        if not members:
            return await ctx.send(
                f"Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            )

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

                try:
                    await ctx.guild.kick(member, reason=reason)
                except Forbidden:
                    await ctx.send(
                        f"I can't kick {member.mention} (No permission or the member is higher than me on the hierarchy)"
                    )
                    return
                await ctx.send(
                    f"{member.mention} has been kicked by {ctx.author.mention} for {reason}!"
                )

    @commands.command(usage="(user) [reason];[ban duration]", hidden=True)
    @checks.is_mod()
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
        reason = r_and_d[0] or "No Reason"
        try:
            min_ban = int(r_and_d[1])
        except ValueError:
            await ctx.send(
                f"**WARNING**: {r_and_d[1]} is not a valid number, value `0` is used instead."
            )
            min_ban = 0

        if not members:
            return await ctx.send(
                f"Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            )

        for member in members:
            if self.bot.user == member:  # Just why would you want to mute him?
                await ctx.send(f"You're not allowed to ban ziBot!")
            else:
                try:
                    await member.send(
                        f"You have been banned from {ctx.guild.name} for {reason}!"
                    )
                except Forbidden:
                    self.logger.error(
                        "discord.errors.Forbidden: Can't send DM to member"
                    )

                try:
                    await ctx.guild.ban(member, reason=reason, delete_message_days=0)
                except Forbidden:
                    await ctx.send(
                        f"I can't ban {member.mention} (No permission or the member is higher than me on the hierarchy)"
                    )
                    return
                duration = ""
                if min_ban > 0:
                    duration = f" ({min_ban} minutes)"
                await ctx.send(
                    f"{member.mention} has been banned by {ctx.author.mention} for {reason}!{duration}"
                )

            if min_ban > 0:
                await asyncio.sleep(min_ban * 60)
                await ctx.guild.unban(member, reason="timed out")

    @commands.command(usage="(user)", hidden=True)
    @checks.is_mod()
    async def unban(self, ctx, members: commands.Greedy[discord.User]):
        """Unban a member."""
        if not members:
            return await ctx.send(
                f"Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            )

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
            else:
                await ctx.send(
                    f"{member.mention} has been unbanned by {ctx.author.mention}!"
                )

    @commands.group()
    @checks.is_mod()
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

    @commands.group()
    @checks.is_mod()
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
    @checks.has_guild_permissions(manage_emojis=True)
    async def emoji_add(
        self, ctx, name: Optional[str], emote_pic: Optional[discord.PartialEmoji]
    ):
        """Add emoji to a server."""
        # Get emote_pic from an emote
        if emote_pic and isinstance(emote_pic, discord.PartialEmoji):
            async with self.bot.session.get(str(emote_pic.url)) as f:
                emote_pic = await f.read()
        # Get emote_pic from embeds
        elif ctx.message.embeds:
            data = ctx.message.embeds[0]
            if data.type == "image":
                async with self.bot.session.get(data.url) as f:
                    emote_pic = await f.read()
            else:
                return await em_ctx_send_error(
                    ctx, "Emoji only supports `.png`, `.jpg`, and `.gif` filetype"
                )
        else:
            emote_pic = None

        # Check if it has attachments
        if ctx.message.attachments and not emote_pic:
            for attachment in ctx.message.attachments:
                emote_pic = await attachment.read()

        # This look ugly but sure why not
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

        # Try to add new emoji, if fails send error
        try:
            added_emote = await ctx.guild.create_custom_emoji(
                name=name, image=emote_pic
            )
        except Forbidden:
            await em_ctx_send_error(
                ctx, "Bot need **Manage Emojis** permission for this command!"
            )
            return
        except discord.InvalidArgument as err:
            if err == "Unsupported image type given":
                return await em_ctx_send_error(
                    ctx, "Emoji only supports `.png`, `.jpg`, and `.gif` filetype"
                )

        # Just embed stuff to give user info that the bot successfully added an emoji
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
    bot.add_cog(Moderation(bot))
