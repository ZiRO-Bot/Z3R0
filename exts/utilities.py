"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import asyncio

import discord
import pyparsing as pyp
import re
import sys


from core.mixin import CogMixin
from decimal import Overflow, InvalidOperation
from discord.ext import commands
from exts.api.piston import Piston
from exts.api.google import Google
from exts.api.googletrans import GoogleTranslate
from exts.utils.format import ZEmbed
from exts.utils.other import (
    NumericStringParser,
    parseCodeBlock,
    encodeMorse,
    decodeMorse,
)


class Utilities(commands.Cog, CogMixin):
    """Useful commands."""

    icon = "🔧"
    cc = True

    def __init__(self, bot):
        super().__init__(bot)
        self.piston = Piston(session=self.bot.session, loop=self.bot.loop)
        self.googletrans = GoogleTranslate(session=self.bot.session)
        self.googlesearch = Google(session=self.bot.session)

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
        except Exception as exc:
            return await ctx.send("I couldn't read that expression properly.")

        e = ZEmbed.default(
            ctx,
            fields=[
                ("Equation", discord.utils.escape_markdown(equation)),
                ("Result", formattedResult),
                ("Raw Result", result),
            ],
        )
        e.set_author(name="Simple Math Evaluator", icon_url=ctx.bot.user.avatar_url)
        return await ctx.try_reply(embed=e)

    @commands.command(
        aliases=("exec", "run"),
        brief="Execute a code",
        description="Execute a code\nWill executes python code by default",
        extras=dict(example=('execute print("Hello World")',)),
    )
    async def execute(self, ctx, *, argument):
        lang, code = parseCodeBlock(argument)

        f = discord.File("./assets/img/piston.png", filename="piston.png")

        msg = await ctx.try_reply(
            embed=ZEmbed.loading().set_author(
                name="Piston API", icon_url="attachment://piston.png"
            ),
            file=f,
        )

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

        await msg.edit(embed=e)

    @commands.command(
        aliases=("tr", "trans"),
        brief="Translate a text",
        extras=dict(
            example=("translate fr->en Bonjour", "trans id Hola", "tr en<-ja こんにちは")
        ),
    )
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
        e = ZEmbed.default(ctx)
        e.set_author(
            name="Google Translate", icon_url="https://translate.google.com/favicon.ico"
        )
        e.add_field(
            name="Source [{}]".format(translated.source), value=translated.origin
        )
        e.add_field(
            name="Translated [{}]".format(translated.dest), value=str(translated)
        )
        return await ctx.try_reply(embed=e)

    @commands.command(
        brief="Encode a text into morse code",
    )
    async def morse(self, ctx, *, text):
        try:
            await ctx.try_reply(f"`{encodeMorse(text)}`")
        except KeyError:
            await ctx.error(
                "Symbols/accented letters is not supported (yet?)", title="Invalid text"
            )

    @commands.command(
        aliases=("demorse",),
        brief="Decode a morse code",
        usage="(morse code)",
    )
    async def unmorse(self, ctx, *, code):
        try:
            await ctx.try_reply(f"`{decodeMorse(code)}`")
        except ValueError:
            await ctx.error("Invalid morse code!")

    @commands.command(aliases=("g",))
    async def google(self, ctx, *, query: str):
        msg = await ctx.try_reply(embed=ZEmbed.loading(title="Searching..."))
        results = await self.googlesearch.search(query)

        if results is None:
            await msg.delete()
            return await ctx.error(
                "Your search - {} - did not match any documents.".format(query),
                title="Not found!",
            )

        e = ZEmbed.default(ctx, title="Google Search: {}...".format(query))

        e.set_footer(text=results["stats"])

        complementary = results["complementary"]
        special = results["special"]
        limit = 3

        if complementary is not None:
            limit -= 1
            e.add_field(
                name=f"{complementary.title or 'Unknown'}",
                value=(
                    f"`{complementary.subtitle or 'Unknown'}`\n"
                    if complementary.subtitle
                    else ""
                )
                + (
                    complementary.description + "\n"
                    if complementary.description
                    else ""
                )
                + "\n".join([f"**{i}**`{j}`" for i, j in complementary.info])
            )

        if special:
            limit -= 1
            e.add_field(
                name=str(special.type).title(),
                value="\n".join(special.content),
            )

        for res in results["web"][:limit]:
            try:
                content = res.contents[0]
            except IndexError:
                content = ""
            e.add_field(name=res.title, value=f"{res.link}\n{content}", inline=False)

        await msg.delete()
        await ctx.try_reply(embed=e)


def setup(bot):
    bot.add_cog(Utilities(bot))
