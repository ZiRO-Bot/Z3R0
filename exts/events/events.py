"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any, Dict, Optional

import discord
import prettify_exceptions
import pytz
import TagScriptEngine as tse
from discord.ext import commands

from core import errors
from core.embed import ZEmbed
from core.mixin import CogMixin
from utils import tseBlocks
from utils.format import formatMissingArgError
from utils.other import doCaselog, reactsToMessage, utcnow

from ._views import Report


if TYPE_CHECKING:
    from core.bot import ziBot


REASON_REGEX = re.compile(r"^\[\S+\#\d+ \(ID: (\d+)\)\]: (.*)")


# TODO: Move this to exts.utils.other
async def doModlog(
    bot: ziBot,
    guild: discord.Guild,
    member: discord.abc.User,
    moderator: discord.abc.User,
    type: str,
    reason: str = None,
) -> None:
    """Basically handle formatting modlog events"""

    channel = await bot.getGuildConfig(guild.id, "modlogCh", "guildChannels")
    channel = bot.get_channel(channel)

    if moderator.id == bot.user.id:
        # This usually True when mods use moderation commands
        # Or when bots doing automod stuff
        if reason and channel:
            # Get the real moderator
            match = REASON_REGEX.match(reason)
            if match:
                modId = match.group(1)
                moderator = bot.get_user(modId) or await bot.fetch_user(modId)
                reason = match.group(2)

    else:
        # Since moderation is done manually, caselog will be done here
        await doCaselog(
            bot,
            guildId=guild.id,
            type=type,
            modId=moderator.id,
            targetId=member.id,
            reason=reason or "No reason",
        )

    if not channel:
        # No channel found, don't do modlog
        return

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

    def __init__(self, bot: ziBot) -> None:
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

    def getGreetSeed(self, member: discord.Member) -> Dict[str, Any]:
        """For welcome and farewell message"""
        target = tse.MemberAdapter(member)
        guild = tse.GuildAdapter(member.guild)
        return {
            "user": target,
            "member": target,
            "guild": guild,
            "server": guild,
        }

    async def handleGreeting(self, member: discord.Member, type: str) -> None:
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

    @commands.Cog.listener("on_member_join")
    async def onMemberJoin(self, member: discord.Member) -> None:
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

    @commands.Cog.listener("on_member_remove")
    async def onMemberRemove(self, member: discord.Member) -> None:
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

    @commands.Cog.listener("on_member_kick")
    async def onMemberKick(
        self, member: discord.User, entry: discord.AuditLogEntry
    ) -> None:
        await doModlog(
            self.bot, member.guild, entry.target, entry.user, "kick", entry.reason
        )

    @commands.Cog.listener("on_member_ban")
    async def onMemberBan(self, guild: discord.Guild, member: discord.Member) -> None:
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

    @commands.Cog.listener("on_command_error")
    async def onCommandError(self, ctx, error) -> Optional[discord.Message]:
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

        # Errors that should be sent no matter what
        # These errors should have `message` already defined
        defaultError = (
            errors.CCommandAlreadyExists,
            commands.BadArgument,
            errors.MissingMuteRole,
            errors.CCommandNoPerm,
            errors.CCommandDisabled,
        )

        print(type(error))

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
            error, errors.ArgumentError
        ):
            e = formatMissingArgError(ctx, error)
            return await ctx.try_reply(embed=e)

        if isinstance(error, defaultError):
            return await ctx.error(str(error))

        if isinstance(error, errors.HierarchyError):
            return await ctx.error(str(error), title="You're not allowed to do that!")

        if isinstance(error, pytz.UnknownTimeZoneError):
            ctx.command.reset_cooldown(ctx)
            return await ctx.error(
                "You can look them up at https://kevinnovak.github.io/Time-Zone-Picker/",
                title="Invalid timezone",
            )

        if isinstance(error, commands.CommandOnCooldown):
            retryAfter = error.retry_after  # type: ignore
            bot_msg = await ctx.error(
                (
                    "You can use it again in {:.2f} seconds.\n".format(retryAfter)
                    + "Default cooldown: {0.rate} times per {0.per} seconds, per {1}".format(
                        error.cooldown, error.type[0]  # type: ignore
                    )
                ),
                title="Command is on a cooldown!",
            )
            await asyncio.sleep(round(retryAfter))
            return await bot_msg.delete()

        if isinstance(error, commands.CheckFailure):
            # TODO: Change the message
            return await ctx.send("You have no permissions!")

        # Give details about the error
        _traceback = "".join(
            prettify_exceptions.DefaultFormatter().format_exception(
                type(error), error, error.__traceback__  # type: ignore
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
                "Click 'Report Error' button to report the error to {}".format(destName)
                if destName
                else ""
            )
            e = ZEmbed.error(
                title="ERROR: Something went wrong!",
                description=desc,
                # colour=discord.Colour(0x2F3136),
            )
            e.set_footer(text="Waiting for answer...", icon_url=ctx.author.avatar.url)

            view = Report(ctx.author, timeout=60.0)

            msg = await ctx.send(embed=e, view=view)

            await view.wait()

            if not view.value:
                e.set_footer(
                    text="You were too late to answer.", icon_url=ctx.author.avatar.url
                )
                view.report.disabled = True
                await msg.edit(embed=e, view=view)
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
                    icon_url=ctx.author.avatar.url,
                )
                view.report.disabled = True
                await msg.edit(embed=e, view=view)

        except IndexError:
            e = ZEmbed.error(
                title="ERROR: Something went wrong!",
                description=desc,
                # colour=discord.Colour(0x2F3136),
            )
            await ctx.send(embed=e)

        return

    @commands.Cog.listener("on_message_edit")
    async def onMessageEdit(
        self, before: discord.Message, after: discord.Message
    ) -> Optional[discord.Message]:
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

        e.set_author(name=before.author, icon_url=before.author.avatar.url)

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

    @commands.Cog.listener("on_message_delete")
    async def onMessageDelete(
        self, message: discord.Message
    ) -> Optional[discord.Message]:
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

        e.set_author(name=message.author, icon_url=message.author.avatar.url)

        e.description = (
            message.content[:1020] + " ..."
            if len(message.content) > 1024
            else message.content
        )

        return await logCh.send(embed=e)

    @commands.Cog.listener("on_member_update")
    async def onMemberUpdate(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        if after.guild.id != 807260318270619748:
            return

        # TODO: Add user log channel
        channel = after.guild.get_channel(814009733006360597)

        role = after.guild.premium_subscriber_role
        if role not in before.roles and role in after.roles:
            e = ZEmbed(
                description="<:booster:865087663609610241> {} has just boosted the server!".format(
                    after.mention
                ),
                color=self.bot.color,
            )
            await channel.send(embed=e)

    @commands.Cog.listener("on_member_muted")
    async def onMemberMuted(self, member: discord.Member, mutedRole: discord.Object):
        guild = member.guild
        try:
            entries = await guild.audit_logs(
                limit=5, action=discord.AuditLogAction.member_role_update
            ).flatten()
            entry: discord.AuditLogEntry = discord.utils.find(
                lambda e: (e.target == member and e.target._roles.has(mutedRole.id)),
                entries,
            )
        except discord.Forbidden:
            entry = None

        if entry:
            await doModlog(
                self.bot, member.guild, entry.target, entry.user, "muted", entry.reason
            )

    @commands.Cog.listener("on_member_unmuted")
    async def onMemberUnmuted(self, member: discord.Member, mutedRole: discord.Role):
        return
