"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import asyncio
import re
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

import discord
import pytz
from aiohttp.client_exceptions import ClientOSError
from discord.app_commands import AppCommandError
from discord.ext import commands

import tse

from ...core import errors
from ...core.embed import ZEmbed
from ...core.mixin import CogMixin
from ...utils.format import formatMissingArgError, formatPerms, formatTraceback
from ...utils.other import doCaselog, reactsToMessage, utcnow
from ._views import Report


if TYPE_CHECKING:
    from ...core.bot import ziBot


REASON_REGEX = re.compile(r"^\[\S+\#\d+ \(ID: (?P<userId>[0-9]+)\) #(?P<caseNum>[0-9]+)\]: (?P<reason>.*)")


async def doModlog(
    bot: ziBot,
    guild: discord.Guild,
    member: discord.User,
    moderator: discord.User,
    type: str,
    reason: str = None,
    caseNum: Optional[int] = None,
) -> None:
    """Basically handle formatting modlog events"""

    channel = bot.get_channel(await bot.getGuildConfig(guild.id, "modlogCh", "GuildChannels") or 0)

    if moderator.id == bot.user.id:  # type: ignore
        # This usually True when mods use moderation commands
        # Or when bots doing automod stuff
        if reason and channel:
            # Get the real moderator
            match = REASON_REGEX.match(reason)
            if match:
                modId = int(match.group("userId"))
                moderator = bot.get_user(modId) or await bot.fetch_user(modId)
                reason = match.group("reason")
                caseNum = int(match.group("caseNum"))

    else:
        # Since moderation is done manually, caselog will be done here
        caseNum = await doCaselog(
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

    title = type.replace("_", " ").title()
    if caseNum:
        title += " | #{}".format(caseNum)

    e = ZEmbed.minimal(
        title=title,
        description=(
            f"**User**: {member} ({member.mention})\n"
            + (f"**Reason**: {reason}\n" if reason else "")
            + f"**Moderator**: {moderator.mention}"
        ),
    )

    e.set_footer(text=f"ID: {member.id}")
    await channel.send(embed=e)  # type: ignore


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
            tse.ReactBlock(),
        ]
        self.engine = tse.Interpreter(blocks)

        bot.tree.error = self.appCommandError

    # TODO - Finish this handler
    async def appCommandError(self, interaction: discord.Interaction, error: AppCommandError):
        """Error handler for app commands

        Untested, hybrid commands seems to be handled by on_command_error
        """
        await interaction.response.send_message("hmm")
        # await self.onCommandError(await (await self.bot.get_context(None)).from_interaction(interaction), error)

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
        channel = await self.bot.getGuildConfig(member.guild.id, f"{type}Ch", "GuildChannels")
        channel = self.bot.get_channel(channel or 0)
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
            msg = await channel.send(content, embed=embed)  # type: ignore
        except discord.HTTPException:
            msg = await channel.send(content)  # type: ignore
        except AttributeError:
            return

        if msg:
            if react := result.actions.get("react"):
                self.bot.loop.create_task(reactsToMessage(msg, react))

    @commands.Cog.listener("on_member_join")
    async def onMemberJoin(self, member: discord.Member) -> None:
        """Welcome message"""
        await self.handleGreeting(member, "welcome")
        autoRole = await self.bot.getGuildConfig(member.guild.id, "autoRole", "GuildRoles")
        if autoRole:
            try:
                await member.add_roles(
                    discord.Object(id=autoRole),
                    reason="Auto Role using {}".format(self.bot.user),
                )
            except discord.HTTPException:
                # Something wrong happened
                return

    async def getAuditLogs(
        self, target: Union[discord.Guild, discord.Member], limit=1, delay=2, **kwargs
    ) -> discord.AuditLogEntry:
        guild: discord.Guild = target.guild if isinstance(target, discord.Member) else target
        # discord needs a few second to update Audit Logs
        await asyncio.sleep(delay)
        return ([i async for i in guild.audit_logs(limit=limit, **kwargs)])[0]

    @commands.Cog.listener("on_member_remove")
    async def onMemberRemove(self, member: discord.Member) -> None:
        """Farewell message"""
        guild: discord.Guild = member.guild

        with suppress(discord.Forbidden, IndexError):
            entry = await self.getAuditLogs(guild)

            if entry.target == member:

                # TODO: Filters bot's action
                if entry.action == discord.AuditLogAction.kick:
                    self.bot.dispatch("member_kick", member, entry)
                    return

                if entry.action == discord.AuditLogAction.ban:
                    # Intents.bans are disabled to make this works
                    self.bot.dispatch("member_ban", member, entry)
                    return

                if entry.action == discord.AuditLogAction.unban:
                    # Intents.bans are disabled to make this works
                    self.bot.dispatch("member_unban", member, entry)
                    return

        # fallback to farewell message
        return await self.handleGreeting(member, "farewell")

    @commands.Cog.listener("on_member_kick")
    async def onMemberKick(self, member: discord.Member, entry: discord.AuditLogEntry) -> None:
        await doModlog(
            self.bot,
            member.guild,
            entry.target,  # type: ignore
            entry.user,
            "kick",
            entry.reason,
        )

    @commands.Cog.listener("on_member_ban")
    async def onMemberBan(self, guild: discord.Guild, user: discord.User) -> None:
        with suppress(discord.Forbidden, IndexError):
            entry = await self.getAuditLogs(guild)
            if entry.target == user:
                await doModlog(
                    self.bot,
                    guild,
                    entry.target,  # type: ignore
                    entry.user,
                    "ban",
                    entry.reason,
                )

    @commands.Cog.listener("on_member_unban")
    async def onMemberUnban(self, guild: discord.Guild, user: discord.User) -> None:
        with suppress(discord.Forbidden, IndexError):
            entry = await self.getAuditLogs(guild)
            if entry.target == user:
                await doModlog(
                    self.bot,
                    guild,
                    entry.target,  # type: ignore
                    entry.user,
                    "unban",
                    entry.reason,
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
            errors.DefaultError,
            errors.CCommandAlreadyExists,
            commands.BadArgument,
            errors.MissingMuteRole,
            errors.CCommandNoPerm,
            errors.CCommandDisabled,
            errors.NotNSFWChannel,
        )

        silentError = (
            errors.SilentError,
            commands.CommandNotFound,
            commands.DisabledCommand,
        )

        if isinstance(error, ClientOSError):
            # Lost connection
            self.bot.logger.error("Connection reset by peer")
            return

        if isinstance(error, silentError):
            return

        if isinstance(error, commands.BadUnionArgument):
            if ctx.command.root_parent and ctx.command.root_parent.name == "emoji" and ctx.command.name == "steal":
                return await ctx.error("Unicode is not supported!")

        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, errors.ArgumentError):
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
                    + "Default cooldown: {0.rate} times per {0.per} seconds, per {1}.".format(
                        error.cooldown, error.type[0]  # type: ignore
                    )
                ),
                title="Command is on a cooldown!",
            )
            with suppress(discord.NotFound):
                # Probably already deleted
                await asyncio.sleep(round(retryAfter))
                return await bot_msg.delete()

        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.error(title="This command is not available in DMs")

        if isinstance(error, commands.BotMissingPermissions):
            return await ctx.error(
                "I don't have {} permission(s) to do this.".format(formatPerms(error.missing_permissions)),  # type: ignore
                title="Missing Permission!",
            )

        if isinstance(error, errors.MissingModPrivilege):
            missingPerms = error.missing_permissions
            msg = "You don't have mod role{}to do this.".format(
                f" or {formatPerms(missingPerms)} permission(s) " if missingPerms else " "
            )
            return await ctx.error(msg, title="Missing Permission!")

        if isinstance(error, errors.MissingAdminPrivilege):
            missingPerms = error.missing_permissions
            msg = "You don't have admin{}to do this.".format(
                f" or {formatPerms(missingPerms)} permission(s) " if missingPerms else " "
            )
            return await ctx.error(msg, title="Missing Permission!")

        if isinstance(error, commands.CheckFailure):
            # TODO: Change the message
            return await ctx.error(title="Check failed!")

        # Give details about the error
        _traceback = formatTraceback("", error)
        self.bot.logger.error("Something went wrong! error: {}".format(_traceback))

        desc = "The command was unsuccessful because of this reason:\n```\n{}\n```\n".format(error)
        try:
            # Send embed that when user react with greenTick bot will send it to bot owner or issue channel
            dest = (
                self.bot.get_partial_messageable(self.bot.issueChannel)
                or self.bot.get_user(self.bot.owner_id)
                or (self.bot.get_user(self.bot.master[0]))
            )
            destName = dest if isinstance(dest, discord.User) else "the support server"

            # Embed things
            desc += "Click 'Report Error' button to report the error to {}".format(destName) if destName else ""
            e = ZEmbed.error(
                title="ERROR: Something went wrong!",
                description=desc,
                # colour=discord.Colour(0x2F3136),
            )
            e.set_footer(text="Waiting for answer...", icon_url=ctx.author.display_avatar.url)

            view = Report(ctx.author, timeout=60.0)

            try:
                msg = await ctx.send(embed=e, view=view)
            except discord.Forbidden:
                return

            await view.wait()

            if not view.value:
                e.set_footer(text="You were too late to answer.", icon_url=ctx.author.display_avatar.url)
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
                    icon_url=ctx.author.display_avatar.url,
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
    async def onMessageEdit(self, before: discord.Message, after: discord.Message) -> Optional[discord.Message]:
        if before.author.bot:
            return

        if not (guild := before.guild):
            return

        if before.type != discord.MessageType.default:
            return

        if before.content == after.content:
            return

        logChId = await self.bot.getGuildConfig(guild.id, "purgatoryCh", "GuildChannels")
        if not logChId:
            return

        logCh = self.bot.get_partial_messageable(logChId)

        e = ZEmbed(timestamp=utcnow(), title="Edited Message")

        avatar = before.author.display_avatar

        e.set_author(name=before.author, icon_url=avatar.url)

        e.add_field(
            name="Before",
            value=before.content[:1020] + " ..."
            if len(before.content) > 1024
            else (before.content or "Nothing to see here..."),
        )
        e.add_field(
            name="After",
            value=after.content[:1020] + " ..."
            if len(after.content) > 1024
            else (after.content or "Nothing to see here..."),
        )

        if before.embeds:
            data = before.embeds[0]
            if data.type == "image":
                # and not self.is_url_spoiler(
                #     before.content, data.url
                # ):
                e.set_image(url=data.url)

        if before.attachments:
            _file = before.attachments[0]
            spoiler = _file.is_spoiler()
            if not spoiler and _file.url.lower().endswith(("png", "jpeg", "jpg", "gif", "webp")):
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

        return await logCh.send(content=before.channel.mention, embed=e)  # type: ignore

    @commands.Cog.listener("on_message_delete")
    async def onMessageDelete(self, message: discord.Message) -> Optional[discord.Message]:
        if message.author.bot:
            return

        if not (guild := message.guild):
            return

        if message.type != discord.MessageType.default:
            return

        logChId = await self.bot.getGuildConfig(guild.id, "purgatoryCh", "GuildChannels")
        if not logChId:
            return

        logCh = self.bot.get_partial_messageable(logChId)

        e = ZEmbed(timestamp=utcnow(), title="Deleted Message")

        avatar = message.author.display_avatar

        e.set_author(name=message.author, icon_url=avatar.url)

        e.description = (
            message.content[:1020] + " ..." if len(message.content) > 1024 else (message.content or "Nothing to see here...")
        )

        return await logCh.send(content=message.channel.mention, embed=e)  # type: ignore

    @commands.Cog.listener("on_member_update")
    async def onMemberUpdate(self, before: discord.Member, after: discord.Member):
        if after.guild.id != 807260318270619748:
            return

        # TODO: Add user log channel
        channel = self.bot.get_partial_messageable(814009733006360597)

        role = after.guild.premium_subscriber_role
        if role not in before.roles and role in after.roles:
            e = ZEmbed(
                description="<:booster:865087663609610241> {} has just boosted the server!".format(after.mention),
                color=self.bot.color,
            )
            return await channel.send(embed=e)

        if not before.is_timed_out() and after.is_timed_out():
            entry = await self.getAuditLogs(after.guild, action=discord.AuditLogAction.member_update)

            if entry.target == after:
                await doModlog(
                    self.bot,
                    after.guild,
                    entry.target,  # type: ignore
                    entry.user,
                    "timed_out",
                    entry.reason,
                )
            return

        if before.is_timed_out() and not after.is_timed_out():
            entry = await self.getAuditLogs(after.guild, action=discord.AuditLogAction.member_update)

            if entry.target == after:
                await doModlog(
                    self.bot,
                    after.guild,
                    entry.target,  # type: ignore
                    entry.user,
                    "time-out_removed",
                    entry.reason,
                )

    @commands.Cog.listener("on_member_muted")
    async def onMemberMuted(self, member: discord.Member, mutedRole: discord.Object):
        if not (guild := member.guild):
            # impossible to happened, but sure
            return

        with suppress(discord.Forbidden, IndexError):
            entry = await self.getAuditLogs(guild, action=discord.AuditLogAction.member_role_update)

            if entry.target == member and entry.target._roles.has(mutedRole.id):  # type: ignore
                await doModlog(
                    self.bot,
                    member.guild,
                    entry.target,  # type: ignore
                    entry.user,
                    "mute",
                    entry.reason,
                )

    @commands.Cog.listener("on_member_unmuted")
    async def onMemberUnmuted(self, member: discord.Member, mutedRole: discord.Role):
        if not (guild := member.guild):
            # impossible to happened, but sure
            return

        with suppress(discord.Forbidden, IndexError):
            entry = await self.getAuditLogs(guild, action=discord.AuditLogAction.member_role_update)

            if entry.target == member and not entry.target._roles.has(mutedRole.id):  # type: ignore
                await doModlog(
                    self.bot,
                    member.guild,
                    entry.target,  # type: ignore
                    entry.user,
                    "unmute",
                    entry.reason,
                )

    @commands.Cog.listener("on_message")
    async def onNoNitroEmoji(self, message: discord.Message):
        if message.author.id != 186713080841895936:
            return

        match = re.findall(r";([a-zA-Z0-9\_]{1,32});", message.content)
        if not match:
            return

        emojiName = match[0]
        result = discord.utils.get(self.bot.emojis, name=emojiName)
        if not result:
            return

        return await message.channel.send(message.content.replace(f";{match[0]};", str(result)))
