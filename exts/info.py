import discord
import time


from .utils.infoQuote import *
from discord.ext import commands


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["bi", "about"])
    async def botinfo(self, ctx):
        """Information about me."""
        # --- Edit these stuff to your liking
        author = "ZiRO2264#4572"
        version = "`v3.0.O` - `overhaul`"
        links = {
            "Documentation (Coming Soon)": "",
            "Source Code": "https://github.com/ZiRO-Bot/ziBot",
            "Support Server": "https://discord.gg/sP9xRy6",
        }
        license = "Public Domain"
        # ---

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

    @commands.command(aliases=["p"])
    async def ping(self, ctx):
        """Tell the ping of the bot to the discord servers."""
        start = time.perf_counter()
        e = discord.Embed(
            title="Pong!",
            timestamp=ctx.message.created_at,
            colour=self.bot.colour,
        )
        e.add_field(
            name="<a:loading:776255339716673566> | Websocket",
            value=f"{round(self.bot.latency*1000)}ms",
        )
        e.set_footer(text="Requested by {}".format(str(ctx.author)))
        msg = await ctx.send(embed=e)
        end = time.perf_counter()
        msg_ping = (end - start) * 1000
        e.add_field(
            name="<a:typing:785053882664878100> | Typing",
            value=f"{round(msg_ping)}ms",
            inline=False,
        )
        await msg.edit(embed=e)

    @commands.command(aliases=["av", "userpfp", "pfp"])
    async def avatar(self, ctx, user: discord.User = None):
        """Show member's avatar image."""
        # TODO: Make a converter to do this thing
        if not user:
            if ref := ctx.message.reference:
                # Get referenced message author
                # if user reply to a message while doing this command
                user = (
                    ref.cached_message.author
                    if ref.cached_message
                    else (await ctx.fetch_message(ref.message_id)).author
                )
            else:
                user = ctx.author

        # Embed stuff
        e = discord.Embed(
            title="{}'s Avatar".format(user.name),
            colour=self.bot.colour,
            description="[`JPEG`]({})".format(user.avatar_url_as(format="jpg"))
            + " | [`PNG`]({})".format(user.avatar_url_as(format="png"))
            + " | [`WEBP`]({})".format(user.avatar_url_as(format="webp"))
            + (
                " | [`GIF`]({})".format(user.avatar_url_as(format="gif"))
                if user.is_avatar_animated()
                else ""
            ),
            timestamp=ctx.message.created_at,
        )
        e.set_image(url=user.avatar_url_as(size=1024))
        e.set_footer(
            text="Requested by {}".format(str(ctx.author)),
            icon_url=ctx.author.avatar_url,
        )
        await ctx.reply(embed=e, mention_author=False)


def setup(bot):
    bot.add_cog(Info(bot))
