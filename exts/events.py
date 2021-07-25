"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import asyncio
import discord
import json
import prettify_exceptions
import pytz
import sys
import traceback
import TagScriptEngine as tse


from core import errors
from core.mixin import CogMixin
from discord.ext import commands
from exts.utils import tseBlocks
from exts.utils.format import formatMissingArgError, ZEmbed
from exts.utils.other import reactsToMessage, ArgumentError, utcnow


# TODO: Move this to exts.utils.other
async def doModlog(
    bot,
    guild: discord.Guild,
    member: discord.abc.User,
    moderator: discord.abc.User,
    type: str,
    reason: str = None,
):
    """Basically handle formatting modlog events"""
    channel = await bot.getGuildConfig(guild.id, "modlogCh", "guildChannels")
    channel = bot.get_channel(channel)
    if not channel:
        # No channel found.
        return

    # TODO: Add caselog for modlog

    e = ZEmbed.minimal(
        title="Modlog - {}".format(type.title()),
        description=(
            f"**User**: {member} ({member.mention})\n"
            + (f"**Reason**: {reason}\n" if reason else "")
            + f"**Moderator**: {moderator.mention}"
        ),
    )
    e.set_footer(text=f"ID: {member.id}")
    await channel.send(embed=e)


class EventHandler(commands.Cog, CogMixin):
    """Place for to put random events."""

    def __init__(self, bot):
        super().__init__(bot)

        # TSE stuff
        blocks = [
            tse.LooseVariableGetterBlock(),
            tse.RandomBlock(),
            tse.AssignmentBlock(),
            tse.RequireBlock(),
            tse.EmbedBlock(),
            tseBlocks.ReactBlock(),
        ]
        self.engine = tse.Interpreter(blocks)

    def getGreetSeed(self, member: discord.Member):
        """For welcome and farewell message"""
        target = tse.MemberAdapter(member)
        guild = tse.GuildAdapter(member.guild)
        return {
            "user": target,
            "member": target,
            "guild": guild,
            "server": guild,
        }

    async def handleGreeting(self, member: discord.Member, type: str):
        channel = await self.bot.getGuildConfig(
            member.guild.id, f"{type}Ch", "guildChannels"
        )
        channel = self.bot.get_channel(channel)
        if not channel:
            return

        message = await self.bot.getGuildConfig(member.guild.id, f"{type}Msg")
        if not message:
            message = ("Welcome" if type == "welcome" else "Goodbye") + ", {member}!"

        result = self.engine.process(message, self.getGreetSeed(member))
        embed = result.actions.get("embed")
        # TODO: Make action tag block to ping everyone, here, or role if admin wants it
        content = (
            str(result.body or ("\u200b" if not embed else ""))
            .replace("@everyone", "@\u200beveryone")
            .replace("@here", "@\u200bhere")
        )
        try:
            msg = await channel.send(content, embed=embed)
        except discord.HTTPException:
            msg = await channel.send(content)

        if msg:
            if react := result.actions.get("react"):
                self.bot.loop.create_task(reactsToMessage(msg, react))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Welcome message"""
        await self.handleGreeting(member, "welcome")
        autoRole = await self.bot.getGuildConfig(
            member.guild.id, "autoRole", "guildRoles"
        )
        if autoRole:
            try:
                await member.add_roles(
                    discord.Object(id=autoRole),
                    reason="Auto Role using {}".format(self.bot.user),
                )
            except discord.HTTPException:
                # Something wrong happened
                return

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Farewell message"""
        # TODO: Add muted_member table to database to prevent mute evasion
        try:
            entries = await member.guild.audit_logs(limit=5).flatten()
            entry: discord.AuditLogEntry = discord.utils.find(
                lambda e: e.target == member, entries
            )
        except discord.Forbidden:
            entry = None

        if entry is not None:
            # TODO: Filters bot's action
            if entry.action == discord.AuditLogAction.kick:
                self.bot.dispatch("member_kick", member, entry)
                return

            if entry.action == discord.AuditLogAction.ban:
                return

        return await self.handleGreeting(member, "farewell")

    @commands.Cog.listener()
    async def on_member_kick(self, member: discord.User, entry: discord.AuditLogEntry):
        await doModlog(
            self.bot, member.guild, entry.target, entry.user, "kick", entry.reason
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, member: discord.Member):
        try:
            entries = await guild.audit_logs(
                limit=5, action=discord.AuditLogAction.ban
            ).flatten()
            entry: discord.AuditLogEntry = discord.utils.find(
                lambda e: e.target == member, entries
            )
        except discord.Forbidden:
            entry = None

        if entry is not None:
            await doModlog(
                self.bot, guild, entry.target, entry.user, "ban", entry.reason
            )

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, "on_error"):
            return

        # This prevents any cogs with an overwritten cog_command_error being handled here.
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound) or isinstance(
            error, commands.DisabledCommand
        ):
            return

        if isinstance(error, commands.BadUnionArgument):
            if (
                ctx.command.root_parent
                and ctx.command.root_parent.name == "emoji"
                and ctx.command.name == "steal"
            ):
                return await ctx.error("Unicode is not supported!")

        if isinstance(error, commands.MissingRequiredArgument) or isinstance(
            error, ArgumentError
        ):
            e = formatMissingArgError(ctx, error)
            return await ctx.try_reply(embed=e)

        if (
            isinstance(error, errors.CCommandAlreadyExists)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, errors.MissingMuteRole)
        ):
            return await ctx.error(str(error))

        if isinstance(error, pytz.exceptions.UnknownTimeZoneError):
            ctx.command.reset_cooldown(ctx)
            return await ctx.error(
                "You can look them up at https://kevinnovak.github.io/Time-Zone-Picker/",
                title="Invalid timezone",
            )

        if isinstance(error, commands.CommandOnCooldown):
            bot_msg = await ctx.error(
                (
                    "You can use it again in {:.2f} seconds.\n".format(
                        error.retry_after
                    )
                    + "Default cooldown: {0.rate} times per {0.per} seconds, per {1}".format(
                        error.cooldown, error.cooldown.type[0]
                    )
                ),
                title="Command is on a cooldown!",
            )
            await asyncio.sleep(round(error.retry_after))
            return await bot_msg.delete()

        if isinstance(error, commands.CheckFailure):
            # TODO: Change the message
            return await ctx.send("You have no permissions!")

        # Give details about the error
        _traceback = "".join(
            prettify_exceptions.DefaultFormatter().format_exception(
                type(error), error, error.__traceback__
            )
        )
        self.bot.logger.error("Something went wrong! error: {}".format(_traceback))
        # --- Without prettify
        # print(
        #     "Ignoring exception in command {}:".format(ctx.command), file=sys.stderr
        # )
        # print(_traceback, file=sys.stderr)
        # ---

        desc = "The command was unsuccessful because of this reason:\n```\n{}\n```\n".format(
            error
        )
        try:
            # Send embed that when user react with greenTick bot will send it to bot owner or issue channel
            dest = (
                self.bot.get_channel(self.bot.issueChannel)
                or self.bot.get_user(self.bot.owner_id)
                or (self.bot.get_user(self.bot.master[0]))
            )
            destName = dest if isinstance(dest, discord.User) else "the support server"

            # Embed things
            desc += (
                "React with <:greenTick:767209095090274325> to report the error to {}".format(
                    destName
                )
                if destName
                else ""
            )
            e = ZEmbed.error(
                title="ERROR: Something went wrong!",
                description=desc,
                # colour=discord.Colour(0x2F3136),
            )
            e.set_footer(text="Waiting for answer...", icon_url=ctx.author.avatar_url)
            msg = await ctx.send(embed=e)

            # Report stuff
            await msg.add_reaction("<:greenTick:767209095090274325>")

            def check(reaction, user):
                # Check if user want to report the error message
                return (
                    user == ctx.author
                    and str(reaction.emoji) == "<:greenTick:767209095090274325>"
                )

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=check
                )
            except asyncio.TimeoutError:
                e.set_footer(
                    text="You were too late to answer.", icon_url=ctx.author.avatar_url
                )
                await msg.edit(embed=e)
                try:
                    await msg.clear_reactions()
                except:
                    pass
            else:
                e_owner = ZEmbed.error(
                    title="ERROR: Something went wrong!",
                    description=f"An error occured:\n```\n{error}\n```",
                    # colour=discord.Colour(0x2F3136),
                )
                e_owner.add_field(name="Executor", value=ctx.author)
                e_owner.add_field(name="Message", value=ctx.message.content)
                await dest.send(embed=e_owner)
                e.set_footer(
                    text="Error has been reported to {}".format(destName),
                    icon_url=ctx.author.avatar_url,
                )
                await msg.edit(embed=e)
                try:
                    await msg.clear_reactions()
                except:
                    # Probably in a DM, lets just pass it
                    pass
        except IndexError:
            e = ZEmbed.error(
                title="ERROR: Something went wrong!",
                description=desc,
                # colour=discord.Colour(0x2F3136),
            )
            await ctx.send(embed=e)

        return

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return

        if before.type != discord.MessageType.default:
            return

        if before.content == after.content:
            return

        guild = before.guild

        logCh = guild.get_channel(
            await self.bot.getGuildConfig(guild.id, "purgatoryCh", "guildChannels")
        )
        if not logCh:
            return

        e = ZEmbed(timestamp=utcnow(), title="Edited Message")

        e.set_author(name=before.author, icon_url=before.author.avatar_url)

        e.add_field(
            name="Before",
            value=before.content[:1020] + " ..."
            if len(before.content) > 1024
            else before.content,
        )
        e.add_field(
            name="After",
            value=after.content[:1020] + " ..."
            if len(after.content) > 1024
            else after.content,
        )

        if before.embeds:
            data = before.embeds[0]
            if data.type == "image" and not self.is_url_spoiler(
                before.content, data.url
            ):
                e.set_image(url=data.url)

        if before.attachments:
            _file = before.attachments[0]
            spoiler = _file.is_spoiler()
            if not spoiler and _file.url.lower().endswith(
                ("png", "jpeg", "jpg", "gif", "webp")
            ):
                e.set_image(url=_file.url)
            elif spoiler:
                e.add_field(
                    name="📎 Attachment",
                    value=f"||[{_file.filename}]({_file.url})||",
                    inline=False,
                )
            else:
                e.add_field(
                    name="📎 Attachment",
                    value=f"[{_file.filename}]({_file.url})",
                    inline=False,
                )

        return await logCh.send(embed=e)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        if message.type != discord.MessageType.default:
            return

        guild = message.guild

        logCh = guild.get_channel(
            await self.bot.getGuildConfig(guild.id, "purgatoryCh", "guildChannels")
        )
        if not logCh:
            return

        e = ZEmbed(timestamp=utcnow(), title="Deleted Message")

        e.set_author(name=message.author, icon_url=message.author.avatar_url)

        e.description = (
            message.content[:1020] + " ..."
            if len(message.content) > 1024
            else message.content
        )

        return await logCh.send(embed=e)

    # @commands.Cog.listener()
    # async def on_member_ban(self):

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if after.guild.id != 807260318270619748:
            return

        # TODO: Add user log channel
        channel = after.guild.get_channel(814009733006360597)

        role = after.guild.premium_subscriber_role
        if not role in before.roles and role in after.roles:
            e = ZEmbed(
                description="<:booster:865087663609610241> {} has just boosted the server!".format(
                    after.mention
                ),
                color=self.bot.color,
            )
            await channel.send(embed=e)


def setup(bot):
    bot.add_cog(EventHandler(bot))
