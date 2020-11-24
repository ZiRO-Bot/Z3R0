import asyncio
import asyncpg
import bot
import cogs.utils.checks as checks
import discord
import re

from .utils.paginator import ZiMenu
from discord.ext import commands, menus

class PrefixPageSource(menus.ListPageSource):
    def __init__(self, prefixes):
        super().__init__(entries=prefixes, per_page=5)
        self.prefixes = prefixes
    
    async def format_page(self, menu, prefixes):
        desc = [f"{self.prefixes.index(prefix) + 1}. {prefix}" for prefix in prefixes]
        e = discord.Embed(
            title = "Prefixes", 
            colour = discord.Colour(0xFFFFF0),
            description = "\n".join(desc)
        )
        maximum = self.get_max_pages()
        e.set_footer(text="{0} prefixes{1}".format(len(self.prefixes), f" - Page {menu.current_page + 1}/{maximum}" if maximum > 1 else ""))
        return e

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = self.bot.logger
        self.bot.loop.create_task(self.async_init())
    
    async def async_init(self):
        """
        Create table for anilist if its not exist
        and cache all the data for later.
        """

        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                # Table for guilds' settings
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS 
                    configs (
                        guild_id BIGINT REFERENCES guilds(id) ON DELETE CASCADE NOT NULL,
                        send_error BOOL NOT NULL,
                        msg_welcome TEXT,
                        msg_farewell TEXT
                    )
                    """
                )

    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx):
        """Manage bot's prefix."""
        await ctx.invoke(self.bot.get_command("prefix list"))
        pass

    @prefix.command(name="list")
    async def prefix_list(self, ctx):
        """List bot's prefixes."""
        prefix = bot._callable_prefix(self.bot, ctx.message)
        del prefix[1]
        menus = ZiMenu(PrefixPageSource(prefix))
        await menus.start(ctx)

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
