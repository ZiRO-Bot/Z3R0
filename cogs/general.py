import aiohttp
import asyncio
import core.bot as bot
import datetime
import discord
import json
import logging
import os
import platform
import re
import subprocess
import textwrap
import time

from .errors.weather import CityNotFound
from .utils.formatting import bar_make, realtime
from discord.errors import Forbidden
from discord.ext import commands
from pytz import timezone
from typing import Optional

session = aiohttp.ClientSession()

MORSE_CODE_DICT = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "0": "-----",
    ".": ".-.-.-",
    ", ": "--..--",
    "?": "..--..",
    "'": ".----.",
    "!": "-.-.--",
    "/": "-..-.",
    "-": "-....-",
    "(": "-.--.",
    ")": "-.--.-",
}


def encode(msg):
    morse = ""
    for letter in msg:
        if letter != " ":
            morse += MORSE_CODE_DICT[letter.upper()] + " "
        else:
            morse += "/ "
    return morse


def decode(msg):
    msg = msg.replace("/ ", " ") + " "
    temp = ""
    decoded = ""
    for code in msg:
        if code not in [".", "-", "/", " "] and code.upper() in list(
            MORSE_CODE_DICT.keys()
        ):
            return None
        if code != " ":
            i = 0
            temp += code
        else:
            i += 1
            if i == 2:
                decoded += " "
            else:
                decoded += list(MORSE_CODE_DICT.keys())[
                    list(MORSE_CODE_DICT.values()).index(temp)
                ]
                temp = ""
    return decoded

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("discord")

    def is_mod():
        def predicate(ctx):
            return ctx.author.guild_permissions.manage_channels

        return commands.check(predicate)

    def is_botmaster():
        def predicate(ctx):
            return ctx.author.id in ctx.bot.master

        return commands.check(predicate)

    @commands.command(usage="(language) (code)", brief="Compile code")
    async def compile(self, ctx, language=None, *, code=None):
        """Compile code from a variety of programming languages, powered by <https://wandbox.org/>\n\
           **Example**
           ``>compile python print('Hello World')``"""

        compilers = {
            "bash": "bash",
            "c": "gcc-head-c",
            "c#": "dotnetcore-head",
            "coffeescript": "coffescript-head",
            "cpp": "gcc-head",
            "elixir": "elixir-head",
            "go": "go-head",
            "java": "openjdk-head",
            "javascript": "nodejs-head",
            "lua": "lua-5.3.4",
            "perl": "perl-head",
            "php": "php-head",
            "python": "cpython-3.8.0",
            "ruby": "ruby-head",
            "rust": "rust-head",
            "sql": "sqlite-head",
            "swift": "swift-5.0.1",
            "typescript": "typescript-3.5.1",
            "vim-script": "vim-head",
        }
        if not language:
            await ctx.send(f"```json\n{json.dumps(compilers, indent=4)}```")
        if not code:
            await ctx.send("No code found")
            return
        try:
            compiler = compilers[language.lower()]
        except KeyError:
            await ctx.send("Language not found")
            return
        body = {"compiler": compiler, "code": code, "save": True}
        head = {"Content-Type": "application/json"}
        async with ctx.typing():
            async with self.bot.session.post(
                "https://wandbox.org/api/compile.json",
                headers=head,
                data=json.dumps(body),
            ) as r:
                # r = requests.post("https://wandbox.org/api/compile.json", headers=head, data=json.dumps(body))
                try:
                    response = json.loads(await r.text())
                    # await ctx.send(f"```json\n{json.dumps(response, indent=4)}```")
                    self.logger.info(f"json\n{json.dumps(response, indent=4)}")
                except json.decoder.JSONDecodeError:
                    self.logger.error(f"json\n{r.text}")
                    await ctx.send(f"```json\n{r.text}```")

                try:
                    embed = discord.Embed(title="Compiled code")
                    embed.add_field(
                        name="Output",
                        value=f'```{response["program_message"]}```',
                        inline=False,
                    )
                    embed.add_field(
                        name="Exit code", value=response["status"], inline=True
                    )
                    embed.add_field(
                        name="Link",
                        value=f"[Permalink]({response['url']})",
                        inline=True,
                    )
                    await ctx.send(embed=embed)
                except KeyError:
                    self.logger.error(f"json\n{json.dumps(response, indent=4)}")
                    await ctx.send(f"```json\n{json.dumps(response, indent=4)}```")

    @commands.command(usage="(words)", example="{prefix}morse SOS")
    async def morse(self, ctx, *msg):
        """Encode message into morse code."""
        encoded = encode(" ".join([*msg]))
        if not encoded:
            return
        e = discord.Embed(
            title=f"{ctx.author.name}#{ctx.author.discriminator}",
            description=encoded,
        )
        await ctx.send(embed=e)

    @commands.command(
        usage="(morse code)", aliases=["demorse"], example="{prefix}unmorse ... --- ..."
    )
    async def unmorse(self, ctx, *msg):
        """Decode morse code."""
        decoded = decode(str(" ".join([*msg])))
        if decoded is None:
            await ctx.send(f"{' '.join([*msg])} is not a morse code!")
            return
        e = discord.Embed(
            title=f"{ctx.author.name}#{ctx.author.discriminator}", description=decoded
        )
        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(General(bot))
