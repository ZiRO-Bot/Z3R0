import asyncio.subprocess
import discord
import os
import re
import time
import sys

from .utils.paginator import ZiMenu
from .utils.formatting import realtime
from discord.ext import commands, menus
from asyncio.subprocess import PIPE, STDOUT


SHELL = os.getenv("SHELL") or "/bin/bash"
WINDOWS = sys.platform == "win32"

class ShellResult:
    def __init__(self, status, stdout, stderr):
        self.status = status
        self._stdout = stdout or ""
        self._stderr = stderr or ""
        if stdout is not None:
            self.stdout = stdout.decode("utf-8")
        else:
            self.stdout = None
        if stderr is not None:
            self.stderr = stderr.decode("utf-8")
        else:
            self.stderr = None

    def __repr__(self):
        return f"<Result status={self.status} stdout={len(self._stdout)} stderr={len(self._stderr)}>"


class TextWrapPageSource(menus.ListPageSource):
    def __init__(self, prefix, lang, raw_text, max_size: int = 1024):
        size_limit = len(prefix)*2 + len(lang) + max_size
        text = [raw_text]
        n = 0
        while len(text[n]) > size_limit:
            text.append(text[n][size_limit:])
            text[n] = text[n][:size_limit]
            n += 1
        super().__init__(entries=text, per_page=1)
        self.lang = lang
        self.prefix = prefix + lang + "\n"
        self.suffix = prefix

    async def format_page(self, menu, text):
        e = discord.Embed(
            title="Shell",
            description=self.prefix + text + self.suffix,
            colour=discord.Colour(0xFFFFF0),
        )
        return e


class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Only bot master able to use this cogs."""
        return await ctx.bot.is_owner(ctx.author)

    @commands.command(aliases=["quit"])
    async def force_close(self, ctx):
        """Shutdown the bot."""
        await ctx.send("Shutting down...")
        await ctx.bot.logout()

    @commands.command(usage="(extension)")
    async def unload(self, ctx, ext):
        """Unload an extension."""
        msg = await ctx.send(f"{self.bot.get_emoji(776255339716673566)} Unloading {ext}...")
        try:
            self.bot.unload_extension(f"cogs.{ext}")
            await msg.edit(content=f"{ext} has been unloaded.")
        except commands.ExtensionNotFound:
            await msd.edit(content=f"{ext} doesn't exist!")
        except commands.ExtensionNotLoaded:
            await msg.edit(content=f"{ext} is not loaded!")
        except commands.ExtensionFailed:
            await msg.edit(content=f"{ext} failed to unload! Check the log for details.")
            self.bot.logger.exception(f"Failed to reload extension {ext}:")

    @commands.command(usage="[extension]")
    async def reload(self, ctx, ext: str = None):
        """Reload an extension."""
        if not ext:
            reload_start = time.time()
            exts = list(self.bot.extensions.keys())
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
        
        info = f"{self.bot.get_emoji(776255339716673566)} Reloading `{ext}`..."
        e = discord.Embed(title=info, colour=discord.Colour.rounded())
        
        msg = await ctx.send(embed=e)
        try:
            info = f"`{ext}` has been reloaded."
            self.bot.reload_extension(f"cogs.{ext}")
            # await msg.edit(content=f"{ext} has been reloaded.")
        except commands.ExtensionNotFound:
            info = f"`{ext}` doesn't exist!"
            # await msg.edit(content=f"{ext} doesn't exist!")
        except commands.ExtensionNotLoaded:
            info = f"`{ext}` is not loaded!"
            # await msg.edit(content=f"{ext} is not loaded!")
        except commands.ExtensionFailed:
            info = f"`{ext}` failed to reload! Check the log for details."
            # await msg.edit(content=f"{ext} failed to reload! Check the log for details.")
            self.bot.logger.exception(f"Failed to reload extension {ext}:")
        e = discord.Embed(title=info, colour=discord.Colour.rounded())
        await msg.edit(embed=e)

    @commands.command(usage="(extension)")
    async def load(self, ctx, ext):
        """Load an extension."""
        msg = await ctx.send(f"{self.bot.get_emoji(776255339716673566)} Loading {ext}...")
        try:
            self.bot.load_extension(f"cogs.{ext}")
            await msg.edit(content=f"{ext} has been loaded.")
        except commands.ExtensionNotFound:
            await msg.edit(content=f"{ext} doesn't exist!")
        except commands.ExtensionFailed:
            await msg.edit(content=f"{ext} failed to load! Check the log for details.")
            self.bot.logger.exception(f"Failed to reload extension {ext}:")

    @commands.command()
    async def pull(self, ctx):
        """Update the bot from github."""
        await ctx.invoke(self.bot.get_command("sh"), command="git pull")

    @commands.command()
    async def leave(self, ctx):
        """Leave the server."""
        await ctx.message.guild.leave()

    @commands.command(aliases=["sh"], usage="(shell command)")
    async def shell(self, ctx, *, command: str):
        """Execute shell command from discord. **Use with caution**"""
        if "sudo" in command:
            return

        if WINDOWS:
            sequence = shlex.split(" ".join([*command]))
        else:
            sequence = [SHELL, "-c", " ".join([*command])]
        
        async def run(shell_command):
            p = await asyncio.create_subprocess_shell(
                shell_command,
                stdin=PIPE, 
                stdout=PIPE, 
                stderr=STDOUT
            )
            stdout, stderr = await p.communicate()
            code = p.returncode
            return ShellResult(code, stdout, stderr)

        proc = await run(command)

        def clean_bytes(line):
            """
            Cleans a byte sequence of shell directives and decodes it.
            """
            # lines = line
            # line = []
            # for i in lines:
            #     line.append(i.decode("utf-8"))
            # line = "".join(line)
            text = line.replace("\r", "").strip("\n")
            return re.sub(r"\x1b[^m]*m", "", text).replace("``", "`\u200b`").strip("\n")

        content = (
            clean_bytes(proc.stdout + (" " + proc.stderr if proc.stderr else ""))
            or f"{SHELL}: command not found: {' '.join(command)}"
        )
        menus = ZiMenu(TextWrapPageSource("```", "sh", content))
        return await menus.start(ctx)
    
    @commands.command()
    async def language(self, ctx, language: str=None):
        if not language:
            return await ctx.send(self.bot.i18n.lang)
        self.bot.i18n._set_locale(language)
        return await ctx.send(language)
    
    @commands.command()
    async def languages(self, ctx):
        languages = [f"`{x[:-8]}`" for x in self.bot.i18n.languages]
        return await ctx.send(", ".join(languages))


def setup(bot):
    bot.add_cog(Developer(bot))
