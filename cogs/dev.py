import asyncio
import discord
import os
import re
import sys
import subprocess
import time

from asyncio.subprocess import PIPE, STDOUT
from discord.ext import commands, menus
from cogs.utilities.paginator import ZiMenu


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

        with ShellHandler(command) as reader:
            p = ShellPageSource(("`" * 3) + "sh", "`" * 3, 1024)
            p.add_line(f"$ {command}\n")
            async for line in reader:
                p.add_line(line)

            menus = ZiMenu(p)
            await menus.start(ctx)

    @commands.group(aliases=["sim"])
    async def simulate(self, ctx):
        """Simulate an event."""
        pass

    @simulate.command()
    async def join(self, ctx):
        """Simulate user joining a server."""
        self.bot.dispatch("member_join", ctx.author)

    @commands.command()
    async def pull(self, ctx):
        """Update the bot from github."""
        await ctx.invoke(self.bot.get_command("sh"), command="git pull")


def setup(bot):
    bot.add_cog(Developer(bot))
