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
from exts.utils.format import formatMissingArgError
from exts.utils.other import reactsToMessage, logAction


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
        channel = await self.bot.getGuildConfig(member.guild.id, f"{type}Ch")
        channel = self.bot.get_channel(channel)
        if not channel:
            return

        message = await self.bot.getGuildConfig(member.guild.id, f"{type}Msg")
        if not message:
            message = ("Welcome" if type == "welcome" else "Goodbye") + ", {member}!"

        result = self.engine.process(message, self.getGreetSeed(member))
        embed = result.actions.get("embed")
        try:
            msg = await channel.send(
                result.body or ("\u200b" if not embed else ""), embed=embed
            )
        except discord.HTTPException:
            msg = await channel.send(result.body or ("\u200b" if not embed else ""))

        if msg:
            if react := result.actions.get("react"):
                self.bot.loop.create_task(reactsToMessage(msg, react))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Welcome message"""
        await self.handleGreeting(member, "welcome")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Farewell message"""
        await self.handleGreeting(member, "farewell")

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

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.BadUnionArgument):
            if ctx.command.root_parent.name == "emoji" and ctx.command.name == "steal":
                return await ctx.error("Unicode is not supported!")

        if isinstance(error, commands.MissingRequiredArgument):
            e = formatMissingArgError(ctx, error)
            return await ctx.try_reply(embed=e)

        if isinstance(error, errors.CCommandAlreadyExists):
            return await ctx.try_reply(error)

        if isinstance(error, pytz.exceptions.UnknownTimeZoneError):
            ctx.command.reset_cooldown(ctx)
            return await ctx.reply(
                "That's not a valid timezone. You can look them up at https://kevinnovak.github.io/Time-Zone-Picker/"
            )

        if isinstance(error, commands.CommandOnCooldown):
            bot_msg = await ctx.send(
                f"{ctx.author.mention}, you have to wait {round(error.retry_after, 2)} seconds before using this again"
            )
            await asyncio.sleep(round(error.retry_after))
            return await bot_msg.delete()

        if isinstance(error, commands.CheckFailure):
            # TODO: Change the message
            return await ctx.send("You have no permissions!")

        if isinstance(error, commands.DisabledCommand):
            return

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

        desc = (
            "The command was unsuccessful because of this reason:\n```{}```\n".format(
                error
            )
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
            e = discord.Embed(
                title="Something went wrong!",
                description=desc,
                colour=discord.Colour(0x2F3136),
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
                await msg.clear_reactions()
            else:
                e_owner = discord.Embed(
                    title="Something went wrong!",
                    description=f"An error occured:\n```{error}```",
                    colour=discord.Colour(0x2F3136),
                )
                e_owner.add_field(name="Executor", value=ctx.author)
                e_owner.add_field(name="Message", value=ctx.message.content)
                await dest.send(embed=e_owner)
                e.set_footer(
                    text="Error has been reported to {}".format(destName),
                    icon_url=ctx.author.avatar_url,
                )
                await msg.edit(embed=e)
                await msg.clear_reactions()
        except IndexError:
            e = discord.Embed(
                title="Something went wrong!",
                description=desc,
                colour=discord.Colour(0x2F3136),
            )
            await ctx.send(embed=e)

        return

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return

        return await logAction(self.bot, "msgEdit", before, after)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        return await logAction(self.bot, "msgDel", message)


def setup(bot):
    bot.add_cog(EventHandler(bot))
