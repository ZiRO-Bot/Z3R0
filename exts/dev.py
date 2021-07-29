"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""


from discord.ext import commands
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.features.baseclass import Feature

from core.bot import EXTS_DIR
from exts.utils.format import ZEmbed

# --- For reload all command status
OK = "<:ok:864033138832703498>"
ERR = "<:error:783265883228340245>"


class Developer(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    """Debugging tools for bot devs."""

    icon = "<:verified_bot_developer:748090768237002792>"

    async def cog_check(self, ctx):
        """Only bot master able to use debug cogs."""
        return self.bot.master and ctx.author.id in self.bot.master

    # def notMe():
    #     async def pred(ctx):
    #         return not (ctx.bot.master and ctx.author.id in ctx.bot.master)

    #     return commands.check(pred)

    # @commands.group(invoke_without_command=True)
    # async def test(self, ctx, text):
    #     """Test something."""
    #     await ctx.send(infoQuote.info("Test") + " {}".format(text))

    # @test.command()
    # async def join(self, ctx):
    #     """Simulate user joining a guild."""
    #     self.bot.dispatch("member_join", ctx.author)

    # @test.command(name="leave")
    # async def testleave(self, ctx):
    #     """Simulate user leaving a guild."""
    #     self.bot.dispatch("member_remove", ctx.author)

    # @test.command()
    # async def reply(self, ctx):
    #     """Test reply."""
    #     await ctx.try_reply("", mention_author=True)

    # @test.command()
    # async def error(self, ctx):
    #     """Test error handler."""
    #     raise RuntimeError("Haha error brrr")

    # @test.command()
    # @notMe()
    # async def noperm(self, ctx):
    #     """Test no permission."""
    #     await ctx.send("You have perm")

    @Feature.Command(
        name="jishaku", aliases=["jsk"], invoke_without_command=True, ignore_extra=False
    )
    async def jsk(self, ctx):
        await ctx.try_invoke("botinfo")

    def tryLoadReload(self, extension: str):
        reloadFailMessage = "Failed to reload {}:"
        actionType = (
            "reload"
            if extension in self.bot.extensions
            or f"{EXTS_DIR}.{extension}" in self.bot.extensions
            else "load"
        )
        action: str = getattr(
            self.bot,
            f"{actionType}_extension",
        )
        try:
            try:
                action(extension)
            except:
                action(f"{EXTS_DIR}.{extension}")
        except Exception as exc:
            # await ctx.send("{} failed to reload! Check the log for details.")
            self.bot.logger.exception(reloadFailMessage.format(extension))
            raise exc

    @Feature.Command(parent="jsk", name="load", aliases=("reload",))
    async def jsk_load(self, ctx, *extensions):
        """Reload extension."""
        exts = extensions or self.bot.extensions.copy()
        status = {}
        for extension in exts:
            try:
                self.tryLoadReload(extension)
            except:
                status[extension] = ERR
            else:
                status[extension] = OK

        e = ZEmbed.default(
            ctx,
        )

        if len(exts) > 1:
            e.title = "Extensions Load/Reload Status"
            e.description = "\n".join(
                ["{} | `{}`".format(v, k) for k, v in status.items()]
            )
        else:
            e.title = "{} | {} {}".format(
                status[extension],
                extension,
                "has been loaded/reloaded"
                if status[extension] == OK
                else "failed to load/reload",
            )

        return await ctx.try_reply(embed=e)

    @commands.command(aliases=["reload"])
    async def load(self, ctx, *extensions):
        await self.jsk_load(ctx, *extensions)


def setup(bot):
    bot.add_cog(Developer(bot=bot))
