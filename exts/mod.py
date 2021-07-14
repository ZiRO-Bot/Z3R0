"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import discord
import humanize


from core import checks
from core.converter import TimeAndArgument
from core.mixin import CogMixin
from discord.ext import commands
from exts.timer import Timer, TimerData
from exts.utils.format import ZEmbed, formatDateTime
from exts.utils.other import utcnow
from typing import Union


class Moderation(commands.Cog, CogMixin):
    """Moderation commands."""

    icon = "🛠️"

    @commands.group(
        usage="(user) [limit] [reason]",
        brief="Ban a user, with optional time limit",
        description=(
            "Ban a user, with optional time limit.\n\n Will delete user's "
            "message, use `save` subcommand to ban a user without deleting their "
            "message"
        ),
        extras=dict(example=(
            "ban @User#0000 4y absolutely no reason",
            "ban @User#0000 scam",
            "ban @User#0000 1 minutes",
        )),
        invoke_without_command=True,
    )
    @checks.mod_or_permissions(ban_members=True)
    async def ban(
        self,
        ctx,
        user: Union[discord.Member, discord.User],
        *,
        time: TimeAndArgument = None
    ):
        await self.doBan(ctx, user, time)

    @ban.command(
        usage="(user) [limit] [reason]",
        brief="Ban a user, with time limit without deleting their message",
        description=(
            "Ban a user, with optional time limit without deleting their message"
        ),
        extras=dict(example=(
            "ban save @User#0000 30m bye",
            "ban save @User#0000 annoying",
            "ban save @User#0000 1 minutes",
        )),
    )
    async def save(
        self,
        ctx,
        user: Union[discord.Member, discord.User],
        *,
        time: TimeAndArgument = None
    ):
        await self.doBan(ctx, user, time, saveMsg=True)

    async def doBan(self, ctx, user, time: TimerData, saveMsg=False):
        """Ban function, self-explanatory"""
        defaultReason = "No reason."

        timer: Timer = self.bot.get_cog("Timer")
        if not timer:
            # Incase Timer cog not loaded yet.
            return await ctx.try_reply(
                "Sorry, this command is currently not available. Please try again later"
            )

        # Some checks before attempting to ban the user
        if user.id == ctx.bot.user.id:
            return await ctx.try_reply("Nice try.")
        if user == ctx.guild.owner:
            return await ctx.try_reply("You can't ban guild owner!")
        try:
            if ctx.me.top_role <= user.top_role:
                return await ctx.try_reply(
                    "{}'s top role is higher than mine in the hierarchy!".format(user)
                )
        except AttributeError:
            # Not guild's member
            pass

        # Try getting necessary variables
        try:
            reason = time.arg or defaultReason
            delta = time.delta
            time = time.when
        except AttributeError:
            reason = defaultReason

        desc = "**Reason**: {}".format(reason)
        guildAndTime = ctx.guild.name
        if time is not None:
            desc += "\n**Duration**: {} ({})".format(delta, formatDateTime(time))
            guildAndTime += " until " + formatDateTime(time)
        DMMsg = "You have been banned from {}. Reason: {}".format(guildAndTime, reason)

        try:
            await user.send(DMMsg)
            desc += "\n**DM**: User notified with a direct message."
        except (AttributeError, discord.HTTPException):
            # Failed to send DM
            desc += "\n**DM**: Failed to notify user."

        try:
            await ctx.guild.ban(
                user,
                reason="[{} (ID: {})]:".format(ctx.author, ctx.author.id) + reason,
                delete_message_days=0 if saveMsg else 1,
            )
        except discord.Forbidden:
            return await ctx.try_reply("I don't have permission to ban a user!")

        if time is not None:
            # Temporary ban
            await timer.createTimer(
                time,
                "ban",
                ctx.guild.id,
                ctx.author.id,
                user.id,
                created=utcnow(),
                owner=ctx.bot.user.id,
            )

        e = ZEmbed.default(
            ctx,
            title="Banned {}".format(user),
            description=desc,
        )
        await ctx.send(embed=e)

    @commands.Cog.listener()
    async def on_ban_timer_complete(self, timer: TimerData):
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
            except:
                moderator = "Mod ID {}".format(modId)
            else:
                moderator = modTemplate.format(moderator, modId)
        else:
            moderator = modTemplate.format(moderator, modId)

        await guild.unban(
            discord.Object(id=userId),
            reason="Automatically unban from timer on {} by {}".format(
                formatDateTime(timer.createdAt), moderator
            ),
        )

    @commands.group(invoke_without_command=True)
    async def mute(
        self,
        ctx,
        user: Union[discord.Member, discord.User],
        *,
        time: TimeAndArgument = None
    ):
        pass

    @mute.command(
        name="create",
        aliases=("set",),
        brief="Create or set muted role for mute command",
        extras=dict(example=(
            "mute create",
            "mute create Muted",
            "mute set @mute",
        )),
        usage="[role name]"
    )
    async def muteCreate(self, ctx, name: Union[discord.Role, str] = "Muted"):
        await ctx.try_invoke(
            "role create" if isinstance(name, str) else "role set",
            arguments=str(getattr(name, "id", name)) + " -t muted",
        )


def setup(bot):
    bot.add_cog(Moderation(bot))
