import discord
import os
import re
import subprocess
import sys

from .utils.paginator import ZiMenu
from discord.ext import commands, menus


SHELL = os.getenv("SHELL") or "/bin/bash"
WINDOWS = sys.platform == "win32"

class TextWrapPageSource(menus.ListPageSource):
    def __init__(self, raw_text):
        text = [raw_text]
        n = 0
        while len(text[n]) > 1024:
            if len(text[n]) > 1024:
                text.append(text[n][1024:])
                text[n] = text[n][:1024]
                n += 1
            else:
                break
        super().__init__(entries=text, per_page=1)

    async def format_page(self, menu, text):
        e = discord.Embed(title="Shell", description=f"```sh\n{text}```")
        return e

class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Only bot master able to use this cogs."""
        return await ctx.bot.is_owner(ctx.author)
    
    @commands.command()
    async def get_prefix(self, ctx):
        prefixes = await self.bot.get_raw_guild_prefixes(ctx.guild.id)
        await ctx.send(prefixes)

    @commands.command(aliases=["quit"], hidden=True)
    async def force_close(self, ctx):
        """Shutdown the bot."""
        await ctx.send("Shutting down...")
        await ctx.bot.logout()

    @commands.command(usage="(extension)", hidden=True)
    async def unload(self, ctx, ext):
        """Unload an extension."""
        await ctx.send(f"Unloading {ext}...")
        try:
            self.bot.unload_extension(f"cogs.{ext}")
            await ctx.send(f"{ext} has been unloaded.")
        except commands.ExtensionNotFound:
            await ctx.send(f"{ext} doesn't exist!")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{ext} is not loaded!")
        except commands.ExtensionFailed:
            await ctx.send(f"{ext} failed to unload! Check the log for details.")
            self.bot.logger.exception(f"Failed to reload extension {ext}:")

    @commands.command(usage="[extension]", hidden=True)
    async def reload(self, ctx, ext: str = None):
        """Reload an extension."""
        if not ext:
            reload_start = time.time()
            exts = get_cogs()
            reloaded = []
            error = 0
            for ext in exts:
                try:
                    self.bot.reload_extension(f"{ext}")
                    reloaded.append(f"<:check_mark:747274119426605116>| {ext}")
                except commands.ExtensionNotFound:
                    reloaded.append(f"<:check_mark:747271588474388522>| {ext}")
                    error += 1
                except commands.ExtensionNotLoaded:
                    reloaded.append(f"<:cross_mark:747274119275479042>| {ext}")
                    error += 1
                except commands.ExtensionFailed:
                    self.bot.logger.exception(f"Failed to reload extension {ext}:")
                    reloaded.append(f"<:cross_mark:747274119275479042>| {ext}")
                    error += 1
            reloaded = "\n".join(reloaded)
            embed = discord.Embed(
                title="Reloading all cogs...",
                description=f"{reloaded}",
                colour=discord.Colour(0x2F3136),
            )
            embed.set_footer(
                text=f"{len(exts)} cogs has been reloaded"
                + f", with {error} errors \n"
                + f"in {realtime(time.time() - reload_start)}"
            )
            await ctx.send(embed=embed)
            return
        await ctx.send(f"Reloading {ext}...")
        try:
            self.bot.reload_extension(f"cogs.{ext}")
            await ctx.send(f"{ext} has been reloaded.")
        except commands.ExtensionNotFound:
            await ctx.send(f"{ext} doesn't exist!")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{ext} is not loaded!")
        except commands.ExtensionFailed:
            await ctx.send(f"{ext} failed to reload! Check the log for details.")
            self.bot.logger.exception(f"Failed to reload extension {ext}:")

    @commands.command(usage="(extension)", hidden=True)
    async def load(self, ctx, ext):
        """Load an extension."""
        await ctx.send(f"Loading {ext}...")
        try:
            self.bot.load_extension(f"cogs.{ext}")
            await ctx.send(f"{ext} has been loaded.")
        except commands.ExtensionNotFound:
            await ctx.send(f"{ext} doesn't exist!")
        except commands.ExtensionFailed:
            await ctx.send(f"{ext} failed to load! Check the log for details.")
            self.bot.logger.exception(f"Failed to reload extension {ext}:")
    
    @commands.command(hidden=True)
    async def pull(self, ctx):
        """Update the bot from github."""
        g = git.cmd.Git(os.getcwd())
        embed = discord.Embed(
            title="Git",
            colour=discord.Colour.lighter_gray(),
            timestamp=datetime.datetime.now(),
        )
        try:
            embed.add_field(name="Pulling...", value=f"```bash\n{g.pull()}```")
        except git.exc.GitCommandError as e:
            embed.add_field(name="Pulling...", value=f"```bash\n{e}```")
        await ctx.send(embed=embed)

    @commands.command()
    async def leave(self, ctx):
        """Leave the server."""
        await ctx.message.guild.leave()

    @commands.command(aliases=["sh"], usage="(shell command)", hidden=True)
    async def shell(self, ctx, *command: str):
        """Execute shell command from discord. **Use with caution**"""
        if "sudo" in command:
            return

        if WINDOWS:
            sequence = shlex.split(" ".join([*command]))
        else:
            sequence = [SHELL, "-c", " ".join([*command])]

        proc = subprocess.Popen(sequence, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        def clean_bytes(line):
            """
            Cleans a byte sequence of shell directives and decodes it.
            """
            lines = line
            line = []
            for i in lines:
                line.append(i.decode("utf-8"))
            line = "".join(line)
            text = line.replace("\r", "").strip("\n")
            return re.sub(r"\x1b[^m]*m", "", text).replace("``", "`\u200b`").strip("\n")

        content = clean_bytes(proc.stdout.readlines()) or f"{SHELL}: command not found: {' '.join(command)}"
        menus = ZiMenu(TextWrapPageSource(content))
        return await menus.start(ctx)
        await ctx.send(f"```{content}```")


def setup(bot):
    bot.add_cog(Developer(bot))
