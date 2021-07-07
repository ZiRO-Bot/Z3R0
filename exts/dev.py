"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import asyncio
import discord
import os
import re
import subprocess
import sys
import time


from core.bot import EXTS_DIR
from core.menus import ZMenu
from core.mixin import CogMixin
from exts.utils import infoQuote
from exts.utils.format import ZEmbed
from discord.ext import commands, menus


# --- For reload all command status
OK = "<:greenTick:767209095090274325>"
ERR = "<:redTick:767209263054585856>"


SHELL = os.getenv("SHELL") or "/bin/bash"
WINDOWS = sys.platform == "win32"


def background_reader(stream, loop: asyncio.AbstractEventLoop, callback):
    """
    Reads a stream and forwards each line to an async callback.
    """

    for line in iter(stream.readline, b""):
        loop.call_soon_threadsafe(loop.create_task, callback(line))


class ShellHandler:
    def __init__(
        self, code: str, timeout: int = 90, loop: asyncio.AbstractEventLoop = None
    ):
        if WINDOWS:
            raise TypeError("Windows is not supported!")
        else:
            sequence = [SHELL, "-c", code]

        self.process = subprocess.Popen(
            sequence, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        self.close_code = None

        self.loop = loop or asyncio.get_event_loop()
        self.timeout = timeout

        self.stdout_task = self.make_reader_task(
            self.process.stdout, self.stdout_handler
        )
        self.stderr_task = self.make_reader_task(
            self.process.stderr, self.stderr_handler
        )

        self.queue = asyncio.Queue(maxsize=250)

    @property
    def closed(self):
        """
        Are both tasks done, indicating there is no more to read?
        """

        return self.stdout_task.done() and self.stderr_task.done()

    async def executor_wrapper(self, *args, **kwargs):
        """
        Call wrapper for stream reader.
        """

        return await self.loop.run_in_executor(None, *args, **kwargs)

    def make_reader_task(self, stream, callback):
        """
        Create a reader executor task for a stream.
        """

        return self.loop.create_task(
            self.executor_wrapper(background_reader, stream, self.loop, callback)
        )

    @staticmethod
    def clean_bytes(line):
        """
        Cleans a byte sequence of shell directives and decodes it.
        """

        text = line.decode("utf-8").replace("\r", "").strip("\n")
        return re.sub(r"\x1b[^m]*m", "", text).replace("``", "`\u200b`").strip("\n")

    async def stdout_handler(self, line):
        """
        Handler for this class for stdout.
        """

        await self.queue.put(self.clean_bytes(line))

    async def stderr_handler(self, line):
        """
        Handler for this class for stderr.
        """

        await self.queue.put(self.clean_bytes(b"[stderr] " + line))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.process.kill()
        self.process.terminate()
        self.close_code = self.process.wait(timeout=0.5)

    def __aiter__(self):
        return self

    async def __anext__(self):
        start_time = time.perf_counter()

        while not self.closed or not self.queue.empty():
            try:
                return await asyncio.wait_for(self.queue.get(), timeout=1)
            except asyncio.TimeoutError as exception:
                if time.perf_counter() - start_time >= self.timeout:
                    raise exception

        raise StopAsyncIteration()


class PaginatorSource(commands.Paginator, menus.PageSource):
    def is_paginating(self):
        return self.get_max_pages() > 1

    def get_max_pages(self):
        return len(self.pages)

    async def get_page(self, page_number: int):
        return self.pages[page_number]


class ShellPageSource(PaginatorSource):
    async def format_page(self, menu, text):
        e = discord.Embed(
            title="Shell",
            description=text,
            colour=discord.Colour(0xFFFFF0),
        )
        return e


class Developer(commands.Cog, CogMixin):
    """Debugging tools for bot devs."""

    icon = "<:verified_bot_developer:748090768237002792>"

    async def cog_check(self, ctx):
        """Only bot master able to use debug cogs."""
        return (
            self.bot.master and ctx.author.id in self.bot.master
        )

    def notMe():
        async def pred(ctx):
            return not (ctx.bot.master and ctx.author.id in ctx.bot.master)

        return commands.check(pred)

    @commands.group(invoke_without_command=True)
    async def test(self, ctx, text):
        """Test something."""
        await ctx.send(infoQuote.info("Test") + " {}".format(text))

    @test.command()
    async def join(self, ctx):
        """Simulate user joining a guild."""
        self.bot.dispatch("member_join", ctx.author)

    @test.command(name="leave")
    async def testleave(self, ctx):
        """Simulate user leaving a guild."""
        self.bot.dispatch("member_remove", ctx.author)

    @test.command()
    async def reply(self, ctx):
        """Test reply."""
        await ctx.try_reply("", mention_author=True)

    @test.command()
    async def error(self, ctx):
        """Test error handler."""
        raise RuntimeError("Haha error brrr")

    @test.command()
    @notMe()
    async def noperm(self, ctx):
        """Test no permission."""
        await ctx.send("You have perm")

    def tryReload(self, extension: str):
        reloadFailMessage = "Failed to reload {}:"
        try:
            try:
                self.bot.reload_extension(extension)
            except:
                self.bot.reload_extension(f"{EXTS_DIR}.{extension}")
        except Exception as exc:
            # await ctx.send("{} failed to reload! Check the log for details.")
            self.bot.logger.exception(reloadFailMessage.format(extension))
            raise exc

    @commands.command()
    async def reload(self, ctx, extension: str = None):
        """Reload extension."""
        e = ZEmbed.default(
            ctx,
            title="Something went wrong!".format(extension),
        )
        if extension:
            # reason will always return None unless an exception raised
            try:
                self.tryReload(extension)
            except Exception as exc:
                e.add_field(name="Reason", value=f"```{exc}```")
            else:
                e = ZEmbed.default(
                    ctx,
                    title="{} | {} has been reloaded!".format(OK, extension),
                )
            finally:
                return await ctx.send(embed=e)
        exts = self.bot.extensions.copy()
        status = {}
        for extension in exts:
            try:
                self.tryReload(extension)
            except:
                status[extension] = ERR
            else:
                status[extension] = OK
        e = ZEmbed.default(
            ctx,
            title="All extensions has been reloaded!",
            description="\n".join(
                ["{} | `{}`".format(v, k) for k, v in status.items()]
            ),
        )
        return await ctx.send(embed=e)

    @commands.command()
    async def load(self, ctx, extension: str):
        """Load an extension"""
        try:
            try:
                self.bot.load_extension(extension)
            except:
                self.bot.load_extension(f"{EXTS_DIR}.{extension}")
        except Exception as exc:
            e = ZEmbed.default(
                ctx,
                title="Something went wrong!".format(extension),
            )
            e.add_field(name="Reason", value=f"```{exc}```")
        else:
            e = ZEmbed.default(
                ctx,
                title="{} | {} has been reloaded!".format(OK, extension),
            )
        finally:
            await ctx.send(embed=e)

    @commands.command(aliases=["sh"])
    async def shell(self, ctx, *, command: str):
        """Execute shell command from discord. **Use with caution**"""
        if "sudo" in command:
            return

        with ShellHandler(command) as reader:
            p = ShellPageSource(("`" * 3) + "sh", "`" * 3, 1024)
            p.add_line(f"$ {command}\n")
            async for line in reader:
                p.add_line(line)

            menus = ZMenu(p)
            await menus.start(ctx)


def setup(bot):
    bot.add_cog(Developer(bot))
