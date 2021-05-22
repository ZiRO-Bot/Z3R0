import discord
import exts.utils.dbQuery as dbQuery


from core.errors import CCommandNotFound
from discord.ext import commands


class Admin(commands.Cog):
    """Admin-only commands to configure the bot."""
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db

        self.bot.loop.create_task(self.asyncInit())

    async def asyncInit(self):
        async with self.db.transaction():
            # commands database table
            await self.db.execute(dbQuery.createCommandsTable)
            # commands_lookup database table
            await self.db.execute(dbQuery.createCommandsLookupTable)

    # TODO: Adds custom check with usage limit (
    #     0: Only mods,
    #     1: Partial (Can only add/edit/remove their own command),
    #     2: Full (Can do anything to any existing command in the guild)
    # )
    @commands.group(aliases=["tag", "script"])
    async def command(self, ctx):
        """Manage commands"""
        pass

    @command.command(aliases=["exec"])
    async def run(self, ctx, name: str, argument: str = None):
        """Run a custom command"""
        hardcoded = {"hello": "Hello World!"}
        result = hardcoded.get(name, None)
        if not result:
            raise CCommandNotFound(name)
        return await ctx.send(result)

    @command.command(aliases=["+", "create"])
    async def add(self, ctx, name, *content):
        """Add new command"""
        pass

    @command.command(aliases=["&"])
    async def edit(self, ctx, name, *content):
        """Edit existing command"""
        pass

    @command.command(aliases=["-", "rm"])
    async def remove(self, ctx, name):
        """Remove a command"""
        pass

    @command.command()
    async def disable(self, ctx, name):
        """Disable a command"""
        # This will work for both built-in and user-made commands
        pass

    @command.command()
    async def enable(self, ctx, name):
        """Enable a command"""
        # This will work for both built-in and user-made commands
        pass

    @command.command(aliases=["?"])
    async def info(self, ctx, name):
        """Show information about a command"""
        # Executes {prefix}help {name} if its built-in command
        pass


def setup(bot):
    bot.add_cog(Admin(bot))
