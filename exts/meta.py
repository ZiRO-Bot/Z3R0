import asyncio
import discord


from core.errors import CCommandNotFound
from exts.utils import dbQuery
from discord.ext import commands


# --- NOTE: Edit these stuff to your liking
author = "ZiRO2264#4572"
version = "`v3.0.O` - `overhaul`"
links = {
    "Documentation (Coming Soon)": "",
    "Source Code": "https://github.com/ZiRO-Bot/ziBot",
    "Support Server": "https://discord.gg/sP9xRy6",
}
license = "Public Domain"
# ---


class Meta(commands.Cog):
    """Bot-related commands."""
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

    @command.command(aliases=["/"])
    async def alias(self, ctx, alias, command):
        """Create alias for a command"""
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

    @commands.command()
    async def source(self, ctx):
        """Get link to my source code."""
        await ctx.send("My source code: {}".format(links["Source Code"]))

    @commands.command(aliases=["bi", "about"])
    async def botinfo(self, ctx):
        """Information about me."""

        # Z3R0 Banner
        f = discord.File("./assets/img/banner.png", filename="banner.png")

        e = discord.Embed(
            description=self.bot.description
            + "\n\nThis bot is licensed under **{}**.".format(license),
            timestamp=ctx.message.created_at,
            colour=self.bot.colour,
        )
        e.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar_url)
        e.set_footer(
            text="Requested by {}".format(str(ctx.author)),
            icon_url=ctx.author.avatar_url,
        )
        e.set_image(url="attachment://banner.png")
        e.add_field(name="Author", value=author)
        e.add_field(
            name="Library",
            value="[`zidiscord.py`](https://github.com/null2264/discord.py) - `v{}`".format(
                discord.__version__
            ),
        )
        e.add_field(name="Version", value=version)
        e.add_field(
            name="Links",
            value="\n".join(
                [
                    "- [{}]({})".format(k, v) if v else "- {}".format(k)
                    for k, v in links.items()
                ]
            ),
            inline=False,
        )
        await ctx.send(file=f, embed=e)


def setup(bot):
    bot.add_cog(Meta(bot))
