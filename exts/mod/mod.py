"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from contextlib import suppress
from typing import Optional, Union

import discord
from discord.ext import commands

from core import checks
from core.converter import BannedMember, MemberOrUser, TimeAndArgument
from core.embed import ZEmbed
from core.errors import MissingMuteRole
from core.mixin import CogMixin
from exts.admin.admin import Admin
from exts.timer.timer import Timer, TimerData
from utils.cache import CacheUniqueViolation
from utils.format import formatDateTime
from utils.other import ArgumentError, ArgumentParser, doCaselog, utcnow


class HierarchyError(Exception):
    def __init__(self, message: str = None):
        super().__init__(
            message
            or "My top role is lower than the target's top role in the hierarchy!"
        )


class Moderation(commands.Cog, CogMixin):
    """Moderation commands."""

    icon = "🛠️"

    async def cog_check(self, ctx):
        if not ctx.guild:
            return False
        return await checks.isMod(ctx)

    async def checkHierarchy(self, ctx, user, action: str = None):
        """Check hierarchy stuff"""
        errMsg = None

        if user.id == ctx.bot.user.id:
            errMsg = "Nice try."
        elif user == ctx.guild.owner:
            errMsg = "You can't {} guild owner!".format(action or "do this action to")
        else:
            # compare author and bot's top role vs target's top role
            with suppress(AttributeError):
                if ctx.me.top_role <= user.top_role:
                    errMsg = (
                        "{}'s top role is higher than mine in the hierarchy!".format(
                            user
                        )
                    )

            with suppress(AttributeError):
                if (
                    ctx.author != ctx.guild.owner  # guild owner doesn't need this check
                    and ctx.author.top_role <= user.top_role
                ):
                    errMsg = (
                        "{}'s top role is higher than yours in the hierarchy!".format(
                            user
                        )
                    )

        # errMsg will always None unless check fails
        if errMsg is not None:
            raise HierarchyError(errMsg)

        return True

    async def doModeration(
        self, ctx, user, _time: Optional[TimeAndArgument], action: str, **kwargs
    ):
        """Ban function, self-explanatory"""
        actions = {
            "ban": self.doBan,
            "mute": self.doMute,
            "kick": self.doKick,
        }

        defaultReason = "No reason."

        timer: Timer = self.bot.get_cog("Timer")
        if not timer:
            # Incase Timer cog not loaded yet.
            return await ctx.error(
                "Sorry, this command is currently not available. Please try again later"
            )

        try:
            await self.checkHierarchy(ctx, user, action)
        except HierarchyError as exc:
            return await ctx.error(str(exc))

        time = None
        delta = None

        # Try getting necessary variables
        try:
            reason = _time.arg or defaultReason  # type: ignore # handled by try-except
            delta = _time.delta  # type: ignore
            time = _time.when  # type: ignore
        except AttributeError:
            reason = kwargs.pop("reason", defaultReason) or defaultReason

        desc = "**Reason**: {}".format(reason)
        guildAndTime = ctx.guild.name
        if time is not None:
            desc += "\n**Duration**: {} ({})".format(delta, formatDateTime(time))
            guildAndTime += " until " + formatDateTime(time)

        DMMsg = {
            "ban": "You have been banned from {}. Reason: {}",
            "mute": "You have been muted from {}. Reason: {}",
            "kick": "You have been kicked from {}. Reason: {}",
        }

        try:
            await user.send(DMMsg[action].format(guildAndTime, reason))
            desc += "\n**DM**: User notified with a direct message."
        except (AttributeError, discord.HTTPException):
            # Failed to send DM
            desc += "\n**DM**: Failed to notify user."

        # Do the action
        try:
            await (actions[action])(
                ctx,
                user,
                reason="[{} (ID: {})]: {}".format(ctx.author, ctx.author.id, reason),
                **kwargs,
            )
        except discord.Forbidden:
            return await ctx.try_reply("I don't have permission to ban a user!")

        caseNum = await doCaselog(
            self.bot,
            guildId=ctx.guild.id,
            type=action,
            modId=ctx.author.id,
            targetId=user.id,
            reason=reason,
        )
        if caseNum:
            desc += "\n**Case**: #{}".format(caseNum)

        if time is not None:
            # Temporary ban
            await timer.createTimer(
                time,
                action,
                ctx.guild.id,
                ctx.author.id,
                user.id,
                created=utcnow(),
                owner=ctx.bot.user.id,
            )

        titles = {
            "ban": "Banned {}",
            "mute": "Muted {}",
            "kick": "Kicked {}",
        }

        e = ZEmbed.success(
            title=titles[action].format(user),
            description=desc,
        )
        await ctx.send(embed=e)

    @commands.group(
        usage="(user) [limit] [reason]",
        brief="Ban a user, with optional time limit",
        description=(
            "Ban a user, with optional time limit.\n\n Will delete user's "
            "message, use `save` subcommand to ban a user without deleting their "
            "message. So instead of `>ban @User#0000` you do `>ban save "
            "@User#0000`"
        ),
        extras=dict(
            example=(
                "ban @User#0000 4y absolutely no reason",
                "ban @User#0000 scam",
                "ban @User#0000 1 minutes",
            ),
            perms={
                "bot": "Ban Members",
                "user": "Ban Members",
            },
        ),
        invoke_without_command=True,
    )
    @checks.mod_or_permissions(ban_members=True)
    async def ban(
        self,
        ctx,
        user: Union[discord.Member, discord.User],
        *,
        time: TimeAndArgument = None,
    ):
        await self.doModeration(ctx, user, time, "ban")

    @ban.command(
        usage="(user) [limit] [reason]",
        brief="Ban a user, with time limit without deleting their message",
        description=(
            "Ban a user, with optional time limit without deleting their message"
        ),
        extras=dict(
            example=(
                "ban save @User#0000 30m bye",
                "ban save @User#0000 annoying",
                "ban save @User#0000 1 minutes",
            )
        ),
    )
    async def save(
        self,
        ctx,
        user: Union[discord.Member, discord.User],
        *,
        time: TimeAndArgument = None,
    ):
        await self.doModeration(ctx, user, time, "ban", saveMsg=True)

    @commands.command(
        brief="Unban a member",
        extras=dict(example=("unban @Someone Wrong person", "unban @Someone")),
    )
    async def unban(self, ctx, member: BannedMember, *, reason: str = "No reason"):
        await ctx.guild.unban(member.user, reason=reason)
        e = ZEmbed.success(
            title="Unbanned {} for {}".format(member.user, reason),
        )
        await ctx.try_reply(embed=e)

    async def doBan(self, ctx, user: discord.User, /, reason: str, **kwargs):
        saveMsg = kwargs.pop("saveMsg", False)

        await ctx.guild.ban(
            user,
            reason=reason,
            delete_message_days=0 if saveMsg else 1,
        )

    @commands.Cog.listener("on_ban_timer_complete")
    async def onBanTimerComplete(self, timer: TimerData):
        """Automatically unban."""
        guildId, modId, userId = timer.args
        await self.bot.wait_until_ready()

        guild = self.bot.get_guild(guildId)
        if not guild:
            return

        try:
            moderator = guild.get_member(modId) or await guild.fetch_member(modId)
        except discord.HTTPException:
            moderator = None

        modTemplate = "{} (ID: {})"
        if not moderator:
            try:
                moderator = self.bot.fetch_user(modId)
            except BaseException:
                moderator = "Mod ID {}".format(modId)

        moderator = modTemplate.format(moderator, modId)

        try:
            await guild.unban(
                discord.Object(id=userId),
                reason="Automatically unban from timer on {} by {}".format(
                    formatDateTime(timer.createdAt), moderator
                ),
            )
        except discord.NotFound:
            # unbanned manually
            return

    @commands.group(
        brief="Mute a member",
        invoke_without_command=True,
        extras=dict(
            example=(
                "mute @Someone 3h spam",
                "mute @Someone 1d",
                "mute @Someone Annoying",
            ),
            perms={
                "bot": "Manage Roles",
                "user": "Manage Messages",
            },
        ),
    )
    @checks.mod_or_permissions(manage_messages=True)
    async def mute(
        self,
        ctx,
        user: discord.Member,
        *,
        time: TimeAndArgument = None,
    ):
        mutedRoleId = await self.bot.getGuildConfig(
            ctx.guild.id, "mutedRole", "guildRoles"
        )
        if not mutedRoleId:
            raise MissingMuteRole(ctx.clean_prefix) from None

        if user._roles.has(mutedRoleId):
            return await ctx.error(f"{user.mention} is already muted!")

        await self.doModeration(
            ctx, user, time, "mute", prefix=ctx.clean_prefix, mutedRoleId=mutedRoleId
        )

    async def doMute(self, _n, member: discord.Member, /, reason: str, **kwargs):
        mutedRoleId = kwargs.get("mutedRoleId", 0)
        try:
            await member.add_roles(discord.Object(id=mutedRoleId), reason=reason)
        except TypeError:
            pass

    @mute.command(
        name="create",
        aliases=("set",),
        brief="Create or set muted role for mute command",
        extras=dict(
            example=(
                "mute create",
                "mute create Muted",
                "mute set @mute",
            ),
            perms={
                "bot": "Manage Roles",
                "user": "Administrator",
            },
        ),
        usage="[role name]",
    )
    async def muteCreate(self, ctx, name: Union[discord.Role, str] = "Muted"):
        await ctx.try_invoke(
            "role create" if isinstance(name, str) else "role set",
            arguments=f"{getattr(name, 'id', name)} type: muted",
        )

    @commands.command(
        brief="Unmute a member",
        extras=dict(
            perms={
                "bot": "Ban Members",
                "user": "Ban Members",
            },
        ),
    )
    @checks.mod_or_permissions(manage_messages=True)
    async def unmute(self, ctx, member: MemberOrUser, *, reason: str = "No reason"):
        guildId = ctx.guild.id
        mutedRoleId = await Admin.getGuildRole(self.bot, guildId, "mutedRole")
        if not mutedRoleId:
            raise MissingMuteRole(ctx.clean_prefix) from None

        if not member._roles.has(mutedRoleId):
            return await ctx.error(f"{member.mention} is not muted!")

        role = discord.Object(id=mutedRoleId)

        try:
            await member.remove_roles(role, reason=reason)
        except (discord.HTTPException, AttributeError):
            # Failed to remove role, just remove it manually
            await self.manageMuted(member, False, role)
        e = ZEmbed.success(
            title="Unmuted {} for {}".format(member, reason),
        )
        await ctx.try_reply(embed=e)

    @commands.Cog.listener("on_member_update")
    async def onMemberUpdate(self, before: discord.Member, after: discord.Member):
        # Used to manage muted members
        if before.roles == after.roles:
            return

        guildId = after.guild.id
        mutedRoleId = await Admin.getGuildRole(self.bot, guildId, "mutedRole")
        if not mutedRoleId:
            return

        beforeHas = before._roles.has(mutedRoleId)
        afterHas = after._roles.has(mutedRoleId)

        if beforeHas == afterHas:
            return

        await self.manageMuted(after, afterHas, discord.Object(id=mutedRoleId))

    @commands.Cog.listener("on_guild_role_delete")
    async def onMutedRoleDeleted(self, role):
        mutedRoleId = await Admin.getGuildRole(self.bot, role.guild.id, "mutedRole")
        if not mutedRoleId or mutedRoleId != role.id:
            return

        await Admin.setGuildRole(self.bot, role.guild.id, "mutedRole", None)

    @commands.Cog.listener("on_mute_timer_complete")
    async def onMuteTimerComplete(self, timer: TimerData):
        """Automatically unmute."""
        guildId, modId, userId = timer.args
        await self.bot.wait_until_ready()

        guild = self.bot.get_guild(guildId)
        if not guild:
            return

        try:
            moderator = guild.get_member(modId) or await guild.fetch_member(modId)
        except discord.HTTPException:
            moderator = None

        modTemplate = "{} (ID: {})"
        if not moderator:
            try:
                moderator = self.bot.fetch_user(modId)
            except BaseException:
                moderator = "Mod ID {}".format(modId)

        moderator = modTemplate.format(moderator, modId)

        member = guild.get_member(userId)
        mutedRoleId = await Admin.getGuildRole(self.bot, guild.id, "mutedRole")
        if not mutedRoleId:
            return await self.manageMuted(member, False, None)

        role = discord.Object(id=mutedRoleId)

        with suppress(
            discord.NotFound, discord.HTTPException
        ):  # ignore NotFound incase mute role got removed
            await member.remove_roles(
                role,
                reason="Automatically unmuted from timer on {} by {}".format(
                    formatDateTime(timer.createdAt), moderator
                ),
            )
        await self.manageMuted(member, False, role)

    async def getMutedMembers(self, guildId: int):
        # Getting muted members from db/cache
        # Will cache db results automatically
        if (mutedMembers := self.bot.cache.guildMutes.get(guildId)) is None:
            dbMutes = await self.bot.db.fetch_all(
                "SELECT * FROM guildMutes WHERE guildId=:id", values={"id": guildId}
            )

            try:
                mutedMembers = [m for _n, m in dbMutes]
                self.bot.cache.guildMutes.extend(guildId, mutedMembers)
            except ValueError:
                mutedMembers = []
        return mutedMembers

    async def manageMuted(
        self, member: discord.Member, mode: bool, mutedRole: discord.Role
    ):
        """Manage muted members, for anti mute evasion

        mode: False = Deletion, True = Insertion"""

        memberId = member.id
        guildId = member.guild.id

        await self.getMutedMembers(guildId)

        if mode is False:
            # Remove member from mutedMembers list
            try:
                self.bot.cache.guildMutes.remove(guildId, memberId)
            except IndexError:
                # It's not in the list so we'll just return
                return

            async with self.db.transaction():
                await self.db.execute(
                    """
                        DELETE FROM guildMutes
                        WHERE
                            guildId=:guildId AND mutedId=:memberId
                    """,
                    values={"guildId": guildId, "memberId": memberId},
                )
            self.bot.dispatch("member_unmuted", member, mutedRole)

        elif mode is True:
            # Add member to mutedMembers list
            try:
                self.bot.cache.guildMutes.add(guildId, memberId)
            except CacheUniqueViolation:
                # Already in the list
                return

            async with self.db.transaction():
                await self.db.execute(
                    "INSERT INTO guildMutes VALUES (:guildId, :memberId)",
                    values={"guildId": guildId, "memberId": memberId},
                )
            self.bot.dispatch("member_muted", member, mutedRole)

    @commands.Cog.listener("on_member_join")
    async def handleMuteEvasion(self, member: discord.Member):
        """Handle mute evaders"""
        mutedMembers = await self.getMutedMembers(member.guild.id)
        if not mutedMembers:
            return

        if member.id not in mutedMembers:
            # Not muted
            return

        with suppress(MissingMuteRole):
            # Attempt to remute mute evader
            await self.doMute(None, member, "Mute evasion")

    # https://github.com/Rapptz/RoboDanny/blob/0992171592f1b92ad74fe2eb5cf2efe1e9a51be8/bot.py#L226-L281
    async def resolveMemberIds(self, guild, member_ids):
        """Bulk resolves member IDs to member instances, if possible.
        Members that can't be resolved are discarded from the list.
        This is done lazily using an asynchronous iterator.
        Note that the order of the resolved members is not the same as the input.
        Parameters
        -----------
        guild: Guild
            The guild to resolve from.
        member_ids: Iterable[int]
            An iterable of member IDs.
        Yields
        --------
        Member
            The resolved members.
        """

        needs_resolution = []
        for member_id in member_ids:
            member = guild.get_member(member_id)
            if member is not None:
                yield member
            else:
                needs_resolution.append(member_id)

        total_need_resolution = len(needs_resolution)
        if total_need_resolution == 0:
            pass
        elif total_need_resolution >= 1:
            shard = self.get_shard(guild.shard_id)
            if shard.is_ws_ratelimited():
                try:
                    member = await guild.fetch_member(needs_resolution[0])
                except discord.HTTPException:
                    pass
                else:
                    yield member
            else:
                members = await guild.query_members(
                    limit=1, user_ids=needs_resolution, cache=True
                )
                if members:
                    yield members[0]
        elif total_need_resolution <= 100:
            # Only a single resolution call needed here
            resolved = await guild.query_members(
                limit=100, user_ids=needs_resolution, cache=True
            )
            for member in resolved:
                yield member
        else:
            # We need to chunk these in bits of 100...
            for index in range(0, total_need_resolution, 100):
                to_resolve = needs_resolution[index : index + 100]
                members = await guild.query_members(
                    limit=100, user_ids=to_resolve, cache=True
                )
                for member in members:
                    yield member

    @commands.Cog.listener("on_muted_role_changed")
    async def onMutedRoleChanged(self, guild: discord.Guild, role: discord.Role):
        """Handle mute role changed"""
        mutedMembers = await self.getMutedMembers(guild.id)
        if mutedMembers:
            reason = "Merging mute roles"
            async for member in self.resolveMemberIds(guild, mutedMembers):
                if not member._roles.has(role.id):
                    try:
                        await member.add_roles(role, reason=reason)
                    except discord.HTTPException:
                        pass

    @commands.command(
        brief="Kick a member",
        extras=dict(
            example=(
                "kick @Someone seeking attention",
                "kick @Someone",
            ),
            perms={
                "bot": "Kick Members",
                "user": "Kick Members",
            },
        ),
    )
    @checks.mod_or_permissions(kick_members=True)
    async def kick(
        self,
        ctx,
        user: discord.Member,
        *,
        reason: str = None,
    ):
        await self.doModeration(ctx, user, None, "kick", reason=reason)

    async def doKick(self, ctx, member: discord.Member, /, reason: str, **kwargs):
        await member.kick(reason=reason)

    @commands.command(
        brief="Announce something",
        extras=dict(
            example=(
                "announce Hello World!",
                "announce target: everyone msg: Totally important message",
                "announce Exclusive announcement for @role target: @role ch: #test",
            ),
            flags={
                ("channel", "ch",): (
                    "Announcement destination (use Announcement channel "
                    "by default set by `announcement @role` command)"
                ),
                "target": "Ping target (everyone, here, or @role)",
                ("message", "msg"): "Edit/extend announcement message",
            },
        ),
        usage="(message) [options]",
    )
    async def announce(self, ctx, *, arguments: str):
        parsed = await self.parseAnnouncement(arguments)
        annCh = parsed.channel
        if not annCh:
            annCh = await self.bot.getGuildConfig(
                ctx.guild.id, "announcementCh", "guildChannels"
            )
            annCh = ctx.guild.get_channel(annCh)
        else:
            annCh: discord.TextChannel = await commands.TextChannelConverter().convert(
                ctx, annCh
            )

        try:
            target = parsed.target.lstrip("@")
        except AttributeError:
            target = "everyone"

        if target.endswith("everyone") or target.endswith("here"):
            target = f"@{target}"
        else:
            target = await commands.RoleConverter().convert(ctx, target)

        await self.doAnnouncement(ctx, " ".join(parsed.message), target, annCh)

    async def parseAnnouncement(self, arguments: str):
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--target")
        parser.add_argument("--channel", aliases=("--ch",))
        parser.add_argument("message", action="extend", nargs="*")
        parser.add_argument("--message", aliases=("--msg",), action="extend", nargs="+")

        parsed, _ = await parser.parse_known_from_string(arguments)

        if not parsed.message:
            raise ArgumentError("Missing announcement message")

        return parsed

    async def doAnnouncement(
        self, ctx, announcement, target, dest: discord.TextChannel
    ):
        content = str(getattr(target, "mention", target))
        content += f"\n{announcement}"
        await dest.send(content)

    @commands.command(
        brief="Clear the chat",
        usage="(amount of message)",
        extras=dict(
            perms={
                "bot": "Manage Messages",
                "user": "Manage Messages",
            },
        ),
    )
    @checks.mod_or_permissions(manage_messages=True)
    async def clearchat(self, ctx, num):
        try:
            num = int(num)
        except ValueError:
            return await ctx.send(f"{num} is not a valid number!")

        e = ZEmbed.loading(title="Deleting messages...")

        msg = await ctx.send(embed=e)

        def isLoading(m):
            return m != msg

        try:
            deleted_msg = await ctx.message.channel.purge(
                limit=num + 1,
                check=isLoading,
                before=None,
                after=None,
                around=None,
                oldest_first=False,
                bulk=True,
            )
        except discord.Forbidden:
            return await ctx.error(
                "The bot doesn't have `Manage Messages` permission!",
                title="Missing Permission",
            )

        msg_num = max(len(deleted_msg), 0)

        if msg_num == 0:
            resp = "Deleted `0 message` 😔 "
            # resp = "Deleted `0 message` 🙄  \n (I can't delete messages "\
            # "older than 2 weeks due to discord limitations)"
        else:
            resp = "Deleted `{} message{}` ✨ ".format(
                msg_num, "" if msg_num < 2 else "s"
            )

        e = ZEmbed.default(ctx, title=resp)

        await msg.edit(embed=e)
