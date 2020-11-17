import asyncio
import asyncpg
import bot
import cogs.utils.checks as checks
import discord
import re

from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = self.bot.logger

    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx):
        """Manage bot's prefix."""
        await ctx.invoke(self.bot.get_command("prefix list"))
        pass

    @prefix.command(name="list")
    async def prefix_list(self, ctx):
        """List bot's prefixes."""
        prefix = bot._callable_prefix(self.bot, ctx.message)
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
    @checks.is_mod()
    async def prefix_add(self, ctx, *prefixes):
        """Add a new prefix to bot."""
        if not prefixes:
            return
        prefixes = list(prefixes)

        if len(prefixes) < 0:
            return

        await ctx.acquire()

        # get current prefix list
        cur_prefixes = await self.bot.get_raw_guild_prefixes(ctx.db, ctx.guild.id)
        # fetch prefixes that can be added
        new_prefixes = []
        for prefix in prefixes:
            # check if prefix is full
            if len(new_prefixes) + len(cur_prefixes) + 1 > 15:
                break
            # check if prefix already exist
            if prefix not in cur_prefixes and prefix not in new_prefixes:
                new_prefixes.append(prefix)
        # add new prefixes to database and update cache
        if new_prefixes:
            await self.bot.bulk_add_guild_prefixes(ctx.db, ctx.guild.id, new_prefixes)

        await ctx.release()
        return await ctx.send(
            (
                ", ".join(
                    f"`{i}`"
                    for i in new_prefixes
                    if new_prefixes 
                )
                or "No prefix"
            )
            + " has been added!"
        )

    @prefix.command(name="remove", aliases=["rm"], usage="(prefix)")
    @checks.is_mod()
    async def prefix_rm(self, ctx, *prefixes):
        """Remove a prefix from bot."""
        if not prefixes:
            return
        prefixes = list(prefixes)

        if len(prefixes) < 0:
            return

        await ctx.acquire()
        
        # get current prefix list
        cur_prefixes = await self.bot.get_raw_guild_prefixes(ctx.db, ctx.guild.id)
        # fetch prefixes that can be added
        new_prefixes = []
        for prefix in prefixes:
            # check if prefix list is not empty after its removed
            if len(new_prefixes) + len(cur_prefixes) - 1 < 0:
                break
            # check if prefix exist
            if prefix in cur_prefixes and prefix not in new_prefixes:
                new_prefixes.append(prefix)
        if new_prefixes:
            await self.bot.bulk_remove_guild_prefixes(
                ctx.db, ctx.guild.id, new_prefixes
            )

        await ctx.release()
        return await ctx.send(
            (", ".join(f"`{i}`" for i in new_prefixes) or "No prefix")
            + " has been removed!"
        )


def setup(bot):
    bot.add_cog(Admin(bot))
