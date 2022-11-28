"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from __future__ import annotations

import sys
import urllib.parse
from decimal import InvalidOperation, Overflow
from typing import TYPE_CHECKING

import aiohttp
import discord
import pyparsing as pyp
from discord import app_commands
from discord.ext import commands

from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.mixin import CogMixin
from ...utils.api.googletrans import GoogleTranslate
from ...utils.api.piston import Piston
from ...utils.other import NumericStringParser, decodeMorse, encodeMorse, parseCodeBlock


if TYPE_CHECKING:
    from ...core.bot import ziBot


class Utilities(commands.Cog, CogMixin):
    """Useful commands."""

    icon = "🔧"
    cc = True

    def __init__(self, bot: ziBot):
        super().__init__(bot)
        self.piston = Piston(session=self.bot.session, loop=self.bot.loop)
        self.googletrans = GoogleTranslate(session=self.bot.session)

    @commands.command(
        aliases=["calc", "c"],
        brief="Simple math evaluator",
        extras=dict(
            example=(
                "calc 12*6",
                "c 5^5",
                "math 50/2",
            )
        ),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def math(self, ctx, *, equation):
        try:
            result = NumericStringParser().eval(equation)
            if result > sys.maxsize:
                formattedResult = "HUGE NUMBER"
            else:
                formattedResult = "{0:,.1f}".format(result)
        except Overflow:
            formattedResult, result = ("Infinity",) * 2
        except InvalidOperation:
            formattedResult, result = ("ERR",) * 2
        except Exception:
            return await ctx.send("I couldn't read that expression properly.")

        e = ZEmbed.default(
            ctx,
            fields=[
                ("Equation", discord.utils.escape_markdown(equation)),
                ("Result", formattedResult),
                ("Raw Result", result),
            ],
        )
        e.set_author(name="Simple Math Evaluator", icon_url=ctx.bot.user.avatar.url)
        return await ctx.try_reply(embed=e)

    @commands.command(
        aliases=("exec", "run"),
        brief="Execute a code",
        description=(
            "Execute a code\n"
            "Will executes python code by default if there's no language specified\n\n"
            "**Usage**:\n"
            ">execute \`\`\`language\ncodes\n\`\`\`\n"  # type: ignore # noqa: W605
            ">execute \`python code\`\n"  # type: ignore # noqa: W605
        ),
        # extras=dict(example=('execute print("Hello World")',)),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def execute(self, ctx, *, argument):
        lang, code = parseCodeBlock(argument)

        async with ctx.loading():
            f = discord.File("./assets/img/piston.png", filename="piston.png")
            executed = await self.piston.run(lang, code)

            e = ZEmbed.default(ctx)
            e.set_author(
                name="Piston API - {}-{}".format(executed.language, executed.version),
                icon_url="attachment://piston.png",
            )

            if executed.message:
                e.description = "```diff\n- {}```".format(executed.message)
            else:
                e.description = "```ini\n{}\n[status] Return code {}```".format(
                    executed.stderr or executed.stdout, executed.code
                )

            await ctx.try_reply(embed=e, file=f)

    @commands.command(
        aliases=("tr", "trans"),
        brief="Translate a text",
        extras=dict(example=("translate fr->en Bonjour", "trans id Hola", "tr en<-ja こんにちは")),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def translate(self, ctx, language, *, text):
        # parse "source->dest" or "dest<-source"
        arrow = pyp.Literal("->") | pyp.Literal("<-")
        lang = pyp.Word(pyp.alphas) + pyp.Optional(arrow + pyp.Word(pyp.alphas))
        parsed = lang.parseString(language)

        kwargs = {}
        try:
            kwargs["dest"] = parsed[2] if parsed[1] == "->" else parsed[0]
            kwargs["source"] = parsed[0] if parsed[1] == "->" else parsed[2]
        except IndexError:
            kwargs["dest"] = parsed[0]

        translated = await self.googletrans.translate(text, **kwargs)
        if not translated:
            return await ctx.error("Translation failed. Please try again later...")

        e = ZEmbed.default(ctx)
        e.set_author(name="Google Translate", icon_url="https://translate.google.com/favicon.ico")
        e.add_field(name="Source [{}]".format(translated.source), value=translated.origin)
        e.add_field(name="Translated [{}]".format(translated.dest), value=str(translated))
        return await ctx.try_reply(embed=e)

    @commands.command(
        brief="Encode a text into morse code",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def morse(self, ctx, *, text):
        try:
            await ctx.try_reply(f"`{encodeMorse(text)}`")
        except KeyError:
            await ctx.error("Symbols/accented letters is not supported (yet?)", title="Invalid text")

    @commands.command(
        aliases=("demorse",),
        brief="Decode a morse code",
        usage="(morse code)",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unmorse(self, ctx, *, code):
        try:
            await ctx.try_reply(f"`{decodeMorse(code)}`")
        except ValueError:
            await ctx.error("Invalid morse code!")

    @commands.hybrid_command(
        aliases=("google", "g"),
        description="Search the Internet",
    )
    @app_commands.rename(query="keyword")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def search(self, ctx: Context, *, query: str):
        if not ctx.interaction:
            msg = await ctx.try_reply(embed=ZEmbed.loading(title="Searching..."))
        else:
            await ctx.defer()

        async with ctx.session.get("https://api.palembani.xyz/search?q=" + urllib.parse.quote(query)) as resp:
            result = await resp.json()

            if not result:
                if not ctx.interaction:
                    await msg.delete()  # type: ignore
                return await ctx.error(
                    "Your search - {} - did not match any documents.".format(query),
                    title="Not found!",
                )

            e = ZEmbed.default(ctx)
            e.set_author(name="Search result for '{}'".format(query))

            resultStats = result["stats"]
            resultCount = resultStats["count"]
            resultDuration = resultStats["duration"]
            e.set_footer(text=(f"About {resultCount:,} results ({resultDuration['value']}" + f" {resultDuration['unit']})"))

            special = result.get("special")
            complementary = result.get("complementary")
            limit = 3

            if special:
                limit -= 1
                specialTitle: str = special["title"]
                specialContent = special["content"]

                i = specialTitle.lower()
                if i.startswith("currency"):
                    from_ = specialContent["from"]
                    to = specialContent["to"]

                    e.add_field(
                        name=f"Rich Card Info: `{special['title'].title()}`",
                        value=(
                            f"`{from_['value']} {from_['currency']}` equals\n"
                            + f"**`{to['value']}` {to['currency']}**\n"
                            + f"Last updated: `{specialContent['last_updated']}`"
                        ),
                        inline=False,
                    )
                elif i.startswith("calculator"):
                    e.add_field(
                        name=f"Rich Card Info: `{special['title'].title()}`",
                        value=" ".join(specialContent.values()),
                        inline=False,
                    )
                else:
                    e.add_field(name=f"Rich Card Info: `{special['title'].title()}`", value=specialContent, inline=False)

            if complementary is not None:
                limit -= 1
                info = ""
                for i in complementary["info"]:
                    a = i.split(":")
                    try:
                        info += f"**{a[0]}**: `{a[1].strip()}` \n"
                    except IndexError:
                        info += f"`{a[0]}`\n"
                e.add_field(
                    name=f"Rich Card Info: `{complementary['title'] or 'Unknown'}`",
                    value=(f"`{complementary['subtitle'] or 'Unknown'}`\n" if complementary["subtitle"] else "")
                    + (complementary["description"] + "\n" if complementary["description"] else "")
                    + info,
                )

            for res in result["sites"][:limit]:
                try:
                    content = res["content"]
                except IndexError:
                    content = ""
                e.add_field(name=res["title"], value=f"{res['link']}\n{content}", inline=False)

            if not ctx.interaction:
                await msg.delete()  # type: ignore
            await ctx.try_reply(embed=e)

    @commands.command(
        brief="Get shorten url's real url. No more rick roll!",
        usage="(shorten url)",
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def realurl(self, ctx, shortenUrl: str):
        async with ctx.loading():
            try:
                async with ctx.bot.session.get(shortenUrl) as res:
                    e = ZEmbed.default(
                        ctx,
                        title="Real URL",
                        description="**Shorten URL**: {}\n**Real URL**: {}".format(shortenUrl, res.real_url),
                    )
                    await ctx.try_reply(embed=e)
            except aiohttp.InvalidURL:
                return await ctx.error("'{}' is not a valid url!".format(shortenUrl), title="Invalid URL")
            except aiohttp.ClientConnectorError:
                return await ctx.error(
                    "Cannot connect to '{}'. Please try again later!".format(shortenUrl),
                    title="Failed to connect",
                )
