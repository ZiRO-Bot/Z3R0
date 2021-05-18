import discord
import exts.utils.dbQuery as dbQuery


from discord.ext import commands


class Admin(commands.Cog):
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
    @commands.group()
    async def command(self, ctx):
        """Manage commands"""
        pass

    @command.command(aliases=["exec"])
    async def run(self, ctx, name, argument = None):
        """Run a custom command"""
        if name != "test":
            raise RuntimeError("Invalid command") 
        return await ctx.send(name)

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
