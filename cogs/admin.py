import asyncio
import asyncpg
import core.bot as bot
import cogs.utils.checks as checks
import discord
import re

from .utils.embed_formatting import em_ctx_send_error, em_ctx_send_success
from .utils.paginator import ZiMenu
from discord.ext import commands, menus


class PrefixPageSource(menus.ListPageSource):
    def __init__(self, prefixes):
        super().__init__(entries=prefixes, per_page=6)
        self.prefixes = prefixes

    async def format_page(self, menu, prefixes):
        desc = [f"{self.prefixes.index(prefix) + 1}. {prefix}" for prefix in prefixes]
        e = discord.Embed(
            title="Prefixes",
            colour=discord.Colour(0xFFFFF0),
            description="\n".join(desc),
        )
        maximum = self.get_max_pages()
        e.set_footer(
            text="{0} prefixes{1}".format(
                len(self.prefixes),
                f" - Page {menu.current_page + 1}/{maximum}" if maximum > 1 else "",
            )
        )
        return e


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = self.bot.logger

    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx):
        """Manage bot's prefix."""
        await ctx.invoke(self.bot.get_command("prefix list"))

    @prefix.command(name="list", aliases=["ls"])
    async def prefix_list(self, ctx):
        """List bot's prefixes."""
        prefix = bot._callable_prefix(self.bot, ctx.message)
        del prefix[1]
        menus = ZiMenu(PrefixPageSource(prefix))
        await menus.start(ctx)

    @prefix.command(name="add", aliases=["+"], usage="(prefix)")
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
                ", ".join(f"`{i}`" for i in new_prefixes if new_prefixes)
                or "No prefix, it may already exist or prefix slot is full."
            )
            + " has been added!"
        )

    @prefix.command(name="remove", aliases=["-", "rm"], usage="(prefix)")
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

    async def get_async_settings(self, ctx, data: str = "*"):
        conn = await ctx.acquire()
        async with conn.transaction():
            data = await conn.fetch(
                "SELECT * FROM configs WHERE guild_id=$1", ctx.guild.id
            )
        return data[0]

    def get_settings(self, ctx, data: str = "*"):
        self.bot.c.execute(
            f"SELECT {data} FROM settings WHERE id=?", (str(ctx.guild.id),)
        )
        settings = self.bot.c.fetchone()
        return settings

    @commands.group()
    @checks.is_mod()
    async def settings(self, ctx):
        """Manage bot's settings."""
        pass

    @settings.command(aliases=["show"])
    async def print(self, ctx):
        """Show current bot settings."""
        settings = await self.get_async_settings(ctx)
        e = discord.Embed(title="Bot's Settings")
        e.add_field(
            name="send_error_msg",
            value=f"`Send error message if command doesn't exist`\nValue: **"
            + str(self.bot.cache[ctx.guild.id]["configs"]["send_error"])
            + "**",
        )
        # e.add_field(
        #     name="disabled_cmds",
        #     value=f"`Disabled commands`\nValue: **"
        #     + (str(settings[2]).replace(",", ", ") if settings[2] else "None")
        #     + "**",
        # )
        e.add_field(
            name="welcome_msg",
            value=f"`Message that sent when a user join the server`\nValue: **"
            + (str(settings[2]) if settings[2] else "Not set")
            + "**",
        )
        e.add_field(
            name="farewell_msg",
            value=f"`Message that sent when a user leaves the server`\nValue: **"
            + (str(settings[3]) if settings[3] else "Not set")
            + "**",
        )
        # e.add_field(
        #     name="mods_only",
        #     value=f"`Commands that only able to be executed by mods`\nValue: **"
        #     + (str(settings[5]).replace(",", ", ") if settings[5] else "None")
        #     + "**",
        # )
        await ctx.send(embed=e)

    @settings.command(aliases=["send_error"])
    async def send_error_msg(self, ctx):
        """Toggle send_error_msg."""

        async def set_send_error(conn, guild_id, value):
            async with conn.transaction():
                await conn.execute(
                    "UPDATE configs SET send_error = $1 WHERE guild_id = $2",
                    value,
                    guild_id,
                )
                self.bot.cache[guild_id]["configs"]["send_error"] = value

        conn = await ctx.db.acquire()
        if self.bot.cache[ctx.guild.id]["configs"]["send_error"]:
            await set_send_error(conn, ctx.guild.id, False)
            await em_ctx_send_success(ctx, "`send_error_msg` has been set to **False**")
        elif not self.bot.cache[ctx.guild.id]["configs"]["send_error"]:
            await set_send_error(conn, ctx.guild.id, True)
            await em_ctx_send_success(ctx, "`send_error_msg` has been set to **True**")
        await ctx.db.release(conn)

    @settings.command(aliases=["welcome"], brief="Change welcome_msg")
    async def welcome_msg(self, ctx, *, message: str = None):
        """Change welcome_msg.
        Special values:
        **{clear}** - clear welcome message (NULL)
        **{mention}** - ping the user
        **{user}** - name of the user
        **{server}** - name of the server
        **{user(id)}** - ID of the user
        **{user(proper)}** - name of the user followed by their discriminator (ziBot#3977)
        **{server(members)}** - number of members on the server"""

        def set_welcome_msg(ctx, value):
            self.bot.c.execute(
                "UPDATE settings SET welcome_msg = ? WHERE id = ?",
                (value, str(ctx.guild.id)),
            )
            self.bot.conn.commit()

        if not message:
            return
        if len(message) > 512:
            return await em_ctx_send_error(
                ctx, "`welcome_msg` can't be longer than 512 characters!"
            )
        if message == "{clear}":
            set_welcome_msg(ctx, None)
            await em_ctx_send_success(ctx, "`welcome_msg` has been cleared")
        else:
            set_welcome_msg(ctx, message)
            await em_ctx_send_success(ctx, f"`welcome_msg` has been set to '{message}'")

    @settings.command(aliases=["farewell", "leave"], brief="Change farewell_msg")
    async def farewell_msg(self, ctx, *, message: str = None):
        """Change farewell_msg.
        Special values:
        **{clear}** - clear farewell message (NULL)
        **{mention}** - ping the user
        **{user}** - name of the user
        **{server}** - name of the server
        **{user(id)}** - ID of the user
        **{user(proper)}** - name of the user followed by their discriminator (ziBot#3977)
        **{server(members)}** - number of members on the server"""

        def set_farewell_msg(ctx, value):
            self.bot.c.execute(
                "UPDATE settings SET farewell_msg = ? WHERE id = ?",
                (value, str(ctx.guild.id)),
            )
            self.bot.conn.commit()

        if not message:
            return
        if len(message) > 512:
            return await em_ctx_send_error(
                ctx, "`farewell_msg` can't be longer than 512 characters!"
            )
        if message == "{clear}":
            set_farewell_msg(ctx, None)
            await em_ctx_send_success(ctx, "`farewell_msg` has been cleared")
        else:
            set_farewell_msg(ctx, message)
            await em_ctx_send_success(
                ctx, f"`farewell_msg` has been set to '{message}'"
            )

    # @settings.command(aliases=["toggle"], usage="(commands)")
    # async def toggle_command(self, ctx, *_commands):
    #     """Toggle commands."""
    #     whitelist = ["help", "settings toggle_command", "settings"]
    #     commands = []
    #     for cmd in _commands:
    #         cmd = self.bot.get_command(str(cmd))
    #         if cmd:
    #             if cmd.qualified_name in whitelist:
    #                 return
    #             commands.append(cmd.qualified_name)
    #     settings = self.get_disabled(ctx) or []
    #     enabled = []
    #     disabled = []
    #     for cmd in commands:
    #         if cmd in settings:
    #             settings.remove(cmd)
    #             enabled.append(cmd)
    #         else:
    #             settings.append(cmd)
    #             disabled.append(cmd)
    #     settings = ",".join(settings)
    #     if not settings:
    #         settings = None
    #     self.bot.c.execute(
    #         "UPDATE settings SET disabled_cmds = ? WHERE id = ?",
    #         (settings, str(ctx.guild.id)),
    #     )
    #     self.bot.conn.commit()
    #     if enabled:
    #         await em_ctx_send_success(ctx, f"`{', '.join(enabled)}` has been enabled!")
    #     if disabled:
    #         await em_ctx_send_success(
    #             ctx, f"`{', '.join(disabled)}` has been disabled!"
    #         )

    # @settings.command(aliases=["mods_only", "toggle_mods", "mods"], usage="(commands)")
    # async def toggle_mods_only(self, ctx, *_commands):
    #     """Toggle mods only commands."""
    #     commands = []
    #     for cmd in _commands:
    #         cmd = self.bot.get_command(str(cmd))
    #         if cmd:
    #             commands.append(cmd.qualified_name)
    #     settings = self.get_mods_only(ctx) or []
    #     enabled = []
    #     disabled = []
    #     for cmd in commands:
    #         if cmd in settings:
    #             settings.remove(cmd)
    #             enabled.append(cmd)
    #         else:
    #             settings.append(cmd)
    #             disabled.append(cmd)
    #     settings = ",".join(settings)
    #     if not settings:
    #         settings = None
    #     self.bot.c.execute(
    #         "UPDATE settings SET mods_only = ? WHERE id = ?",
    #         (settings, str(ctx.guild.id)),
    #     )
    #     self.bot.conn.commit()
    #     if enabled:
    #         await em_ctx_send_success(
    #             ctx, f"`{', '.join(enabled)}` is no longer mods only!"
    #         )
    #     if disabled:
    #         await em_ctx_send_success(ctx, f"`{', '.join(disabled)}` is now mods only!")


def setup(bot):
    bot.add_cog(Admin(bot))
