"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import datetime as dt
import discord


from core.bot import EXTS_DIR
from core.mixin import CogMixin
from exts.utils import infoQuote
from discord.ext import commands


# --- For reload all command status
OK = "<:greenTick:767209095090274325>"
ERR = "<:redTick:767209263054585856>"


class Developer(commands.Cog, CogMixin):
    """Debugging tools for bot devs."""

    async def cog_check(self, ctx):
        """Only bot master able to use debug cogs."""
        return (
            (self.bot.master
            and ctx.author.id in self.bot.master)
            or commands.is_owner().predicate(ctx)
        )

    def notMe():
        async def pred(ctx):
            return not (
                (ctx.bot.master
                and ctx.author.id in ctx.bot.master)
                or commands.is_owner().predicate(ctx)
            )

        return commands.check(pred)


    @commands.group(invoke_without_command=True)
    async def test(self, ctx, text):
        """Test something."""
        await ctx.send(infoQuote.info("Test") + " {}".format(text))

    @test.command()
    async def error(self, ctx):
        """Test error handler."""
        raise RuntimeError("Haha error brrr")

    @test.command()
    @notMe()
    async def noperm(self, ctx):
        """Test no permission."""
        pass

    def tryReload(self, extension: str):
        reloadFailMessage = "Failed to reload {}: {}"
        try:
            try:
                self.bot.reload_extension(extension)
            except:
                self.bot.reload_extension(f"{EXTS_DIR}.{extension}")
        except commands.ExtensionNotFound as exc:
            self.bot.logger.error(reloadFailMessage.format(extension, "Doesn't exist."))
            raise exc
        except commands.ExtensionNotLoaded as exc:
            # await ctx.send("{} is not loaded!")
            self.bot.logger.error(reloadFailMessage.format(extension, "Not loaded."))
            raise exc
        except commands.ExtensionFailed as exc:
            # await ctx.send("{} failed to reload! Check the log for details.")
            self.bot.logger.exception(reloadFailMessage.format(extension, ""))
            raise exc

    @commands.command()
    async def reload(self, ctx, extension: str = None):
        """Reload extension."""
        e = discord.Embed(
            title="Something went wrong!".format(extension),
            colour=self.bot.colour,
            timestamp=dt.datetime.utcnow()
        )
        if extension:
            # reason will always return None unless an exception raised
            reason = None
            try:
                self.tryReload(extension)
            except commands.ExtensionNotFound:
                reason = "{} doesn't exist!".format(extension)
                e.add_field(name="Reason", value=reason)
            except commands.ExtensionNotLoaded:
                reason = "{} is not loaded!".format(extension)
            except commands.ExtensionFailed:
                reason = "{} failed to reload! Check the log for details.".format(extension)
            else:
                e = discord.Embed(
                    title="{} has been reloaded!".format(extension),
                    colour=self.bot.colour,
                    timestamp=dt.datetime.utcnow()
                )
            finally:
                e.set_footer(
                    text="Requested by {}".format(str(ctx.author)),
                    icon_url=ctx.author.avatar_url,
                )
                if reason:
                    e.add_field(name="Reason", value=f"```{reason}```")
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
        e = discord.Embed(
            title="All extensions has been reloaded!",
            description="\n".join(["{} | `{}`".format(v, k) for k, v in status.items()]),
            colour=self.bot.colour,
            timestamp=dt.datetime.utcnow()
        )
        e.set_footer(
            text="Requested by {}".format(str(ctx.author)),
            icon_url=ctx.author.avatar_url,
        )
        return await ctx.send(embed=e)



def setup(bot):
    bot.add_cog(Developer(bot))
