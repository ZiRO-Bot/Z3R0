import asyncio
import discord


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
