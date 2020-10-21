import asyncio
import sys
import traceback

from discord.ext import commands


class ErrorHandler(commands.Cog):
    """Handle errors."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = self.bot.logger

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                f"Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            )

        if isinstance(error, commands.CommandOnCooldown):
            bot_msg = await ctx.send(
                f"{ctx.message.author.mention}," + f" slowdown bud!"
            )
            await asyncio.sleep(round(error.retry_after))
            await bot_msg.delete()
            return

        print("Ignoring exception in command {}:".format(ctx.command), file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
