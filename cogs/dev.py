import asyncio
import discord
import os
import re
import sys

from asyncio.subprocess import PIPE, STDOUT
from discord.ext import commands, menus
from cogs.utilities.paginator import ZiMenu


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
        size_limit = len(prefix) * 2 + len(lang) + max_size
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
        """Only bot master able to use debug cogs."""
        return await ctx.bot.is_owner(ctx.author)

    @commands.command(aliases=["sh"], usage="(shell command)")
    async def shell(self, ctx, *, command: str):
        """Execute shell command from discord. **Use with caution**"""
        if "sudo" in command:
            return

        if WINDOWS:
            return await ctx.send("Windows is not supported!")
        else:
            sequence = [SHELL, "-c", " ".join([*command])]

        async def run(shell_command):
            p = await asyncio.create_subprocess_shell(
                shell_command, stdin=PIPE, stdout=PIPE, stderr=STDOUT
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
    async def pull(self, ctx):
        """Update the bot from github."""
        await ctx.invoke(self.bot.get_command("sh"), command="git pull")


def setup(bot):
    bot.add_cog(Developer(bot))
