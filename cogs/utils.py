import asyncio
import aiohttp
import core.bot as bot
import datetime
import discord
import json
import logging
import re
import time

from aiogoogletrans import Translator
from cogs.utilities.formatting import realtime
from discord.ext import commands, menus

translator = Translator()


class Translated:
    def __init__(self, source, dest, origin, translated):
        self.source = source
        self.destination = dest
        self.origin = origin
        self.translated = translated

    def __str__(self):
        return self.translated

    def __repr__(self):
        return f"<{self.source} -> {self.destination}: origin={self.origin}, translated={self.translated}>"

    @property
    def dest(self):
        return self.destination


class GoogleTranslate:
    def __init__(self, session=None):
        self.session = session or aiohttp.ClientSession()
        self.URL = "https://translate.googleapis.com/translate_a/single?client=gtx&dt=t"

    async def translate(self, source, dest, query):
        async with self.session.get(
            self.URL + f"&sl={source}&tl={dest}&q={query}"
        ) as res:
            _json = json.loads(await res.text())
        return Translated(source, dest, query, _json[0][0][0])


class SearxAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = aiohttp.ClientSession()
        self.engines = ["duckduckgo", "google", "bing"]

    async def get_results(self, query: str) -> dict:
        """
        Search query and get all the results.
        """
        payload = {
            "q": query,
            "format": "json",
            "language": "en-US",
            "safesearch": 1,
            "engines": ",".join(self.engines),
        }
        async with self.session.post(self.base_url, data=payload) as page:
            _json = json.loads(await page.text())
        return _json["results"]


class SearxResultsPageSource(menus.ListPageSource):
    def __init__(self, ctx, results):
        self.ctx = ctx
        super().__init__(entries=results, per_page=1)

    def format_page(self, menu, page):
        e = discord.Embed(
            title=page["title"],
            description=page["content"],
            url=page["pretty_url"],
            colour=discord.Colour.dark_gray(),
        )
        e.set_thumbnail(
            url="https://searx.github.io/searx/_static/searx_logo_small.png"
        )
        maximum = self.get_max_pages()
        e.set_footer(
            text=f"Requested by {self.ctx.author} - Page {menu.current_page + 1}/{maximum}",
            icon_url=self.ctx.author.avatar_url,
        )
        return e


class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("discord")
        self.spoilers = re.compile(r"\|\|(.+?)\|\|")
        self.searx = SearxAPI("https://searx.lukesmith.xyz/")

    def is_url_spoiler(self, text, url):
        spoilers = self.spoilers.findall(text)
        for spoiler in spoilers:
            if url in spoiler:
                return True
        return False

    def get_disabled(self, ctx):
        self.bot.c.execute(
            "SELECT disabled_cmds FROM settings WHERE (id=?)", (str(ctx.guild.id),)
        )
        disabled = self.bot.c.fetchone()
        try:
            disabled_cmds = disabled[0].split(",")
        except AttributeError:
            disabled_cmds = []

        return disabled_cmds

    def get_mods_only(self, ctx):
        self.bot.c.execute(
            "SELECT mods_only FROM settings WHERE (id=?)", (str(ctx.guild.id),)
        )
        mods = self.bot.c.fetchone()
        try:
            mods_only = mods[0].split(",")
        except AttributeError:
            mods_only = []

        return mods_only

    async def bot_check(self, ctx):
        """
        Global checks, owner bypass all checks
        """
        if not ctx.guild:
            return True

        is_owner = await ctx.bot.is_owner(ctx.author)
        if is_owner:
            return True

        cmd_name = ctx.command.root_parent
        if not cmd_name:
            cmd_name = ctx.command.qualified_name

        disabled_cmds = self.get_disabled(ctx)
        if disabled_cmds:
            if cmd_name in disabled_cmds:
                return False
            if ctx.command.qualified_name in disabled_cmds:
                return False

        mods_only = self.get_mods_only(ctx)
        if mods_only and not ctx.author.guild_permissions.manage_channels:
            if cmd_name in mods_only:
                return False
            if ctx.command.qualified_name in mods_only:
                return False

        return True

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        msg_id = payload.message_id
        if msg_id == 746645838586970152:
            guild_id = payload.guild_id
            guild = discord.utils.find(lambda g: g.id == guild_id, self.bot.guilds)
            role = None
            if payload.emoji.name == "🖥️":
                role = discord.utils.get(guild.roles, name="Computer Nerd")
            elif payload.emoji.name == "🇦":
                role = discord.utils.get(guild.roles, name="Weeb")
            elif payload.emoji.name == "🇸":
                role = discord.utils.get(guild.roles, name="Speedrunner")

            if role:
                member = discord.utils.find(
                    lambda m: m.id == payload.user_id, guild.members
                )
                if member:
                    await member.add_roles(role)
                else:
                    print("Member not found")
            else:
                print("Role not found")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        msg_id = payload.message_id
        if msg_id == 746645838586970152:
            guild_id = payload.guild_id
            guild = discord.utils.find(lambda g: g.id == guild_id, self.bot.guilds)
            role = None
            if payload.emoji.name == "🖥️":
                role = discord.utils.get(guild.roles, name="Computer Nerd")
            elif payload.emoji.name == "🇦":
                role = discord.utils.get(guild.roles, name="Weeb")
            elif payload.emoji.name == "🇸":
                role = discord.utils.get(guild.roles, name="Speedrunner")

            if role:
                member = discord.utils.find(
                    lambda m: m.id == payload.user_id, guild.members
                )
                if member:
                    await member.remove_roles(role)
                else:
                    print("Member not found")
            else:
                print("Role not found")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author == self.bot.user:
            return

        self.bot.c.execute(
            "SELECT purge_ch FROM servers WHERE id=?", (str(message.guild.id),)
        )
        try:
            purgatory_ch = self.bot.c.fetchall()[0][0]
        except IndexError:
            return
        if not purgatory_ch:
            return
        purgatory_ch = self.bot.get_channel(purgatory_ch)

        msg = f"**Deleted Message** in {message.channel.mention}"

        embed = discord.Embed(
            description=message.content,
            timestamp=message.created_at,
            colour=discord.Colour.red(),
        )
        embed.set_author(
            name=f"{message.author.name}#{message.author.discriminator}",
            icon_url=message.author.avatar_url,
        )

        if message.embeds:
            data = message.embeds[0]
            if data.type == "image" and not self.is_url_spoiler(
                message.content, data.url
            ):
                embed.set_image(url=data.url)

        if message.attachments:
            _file = message.attachments[0]
            spoiler = _file.is_spoiler()
            if not spoiler and _file.url.lower().endswith(
                ("png", "jpeg", "jpg", "gif", "webp")
            ):
                embed.set_image(url=_file.url)
            elif spoiler:
                embed.add_field(
                    name="📎 Attachment",
                    value=f"||[{_file.filename}]({_file.url})||",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="📎 Attachment",
                    value=f"[{_file.filename}]({_file.url})",
                    inline=False,
                )
        embed.set_footer(text=message.id)
        await purgatory_ch.send(msg, embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return
        message = before

        self.bot.c.execute(
            "SELECT purge_ch FROM servers WHERE id=?", (str(message.guild.id),)
        )
        try:
            purgatory_ch = self.bot.c.fetchall()[0][0]
        except IndexError:
            return
        if not purgatory_ch:
            return
        purgatory_ch = self.bot.get_channel(purgatory_ch)

        msg = f"**Edited Message** in {message.channel.mention}"

        embed = discord.Embed(colour=discord.Colour.red(), timestamp=after.edited_at)
        embed.set_author(
            name=f"{message.author.name}#{message.author.discriminator}",
            icon_url=message.author.avatar_url,
        )
        embed.add_field(
            name="**Original Message**", value=message.content or "\u200b", inline=False
        )
        embed.add_field(name="**New Message**", value=after.content, inline=False)

        if message.embeds:
            data = message.embeds[0]
            if data.type == "image" and not self.is_url_spoiler(
                message.content, data.url
            ):
                embed.set_image(url=data.url)

        if message.attachments:
            _file = message.attachments[0]
            spoiler = _file.is_spoiler()
            if not spoiler and _file.url.lower().endswith(
                ("png", "jpeg", "jpg", "gif", "webp")
            ):
                embed.set_image(url=_file.url)
            elif spoiler:
                embed.add_field(
                    name="📎 Attachment",
                    value=f"||[{_file.filename}]({_file.url})||",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="📎 Attachment",
                    value=f"[{_file.filename}]({_file.url})",
                    inline=False,
                )
        embed.set_footer(text=after.id)
        await purgatory_ch.send(msg, embed=embed)

    @commands.command(aliases=["p"])
    async def ping(self, ctx):
        """Tell the ping of the bot to the discord servers."""
        start = time.perf_counter()
        e = discord.Embed(
            title="Ping",
            description="**API Latency** = Time it takes to recive data from the discord API\n**Response Time** = Time it took send this response to your message\n**Bot Latency** = Time needed to send/edit messages",
            timestamp=ctx.message.created_at,
            colour=discord.Colour(0xFFFFF0),
        )
        e.add_field(name="API Latency", value=f"{round(self.bot.latency*1000)}ms")
        e.set_footer(
            text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
        )
        msg = await ctx.send(embed=e)
        end = time.perf_counter()
        msg_ping = (end - start) * 1000
        e.add_field(
            name="Response Time",
            value=f"{round((msg.created_at - ctx.message.created_at).total_seconds()/1000, 4)}ms",
        )
        e.add_field(name="Bot Latency", value=f"{round(msg_ping)}ms")
        await msg.edit(embed=e)

    @commands.command(
        aliases=["trans"], brief="Translate a text.", usage="(language) (text)"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def translate(self, ctx, lang, *txt):
        """Translate a text.\n\
           **Example**
           ``>translate fr Bonjour``"""
        if not txt:
            await ctx.send("You need to specify the text you want to translate!")
        abbv = {"jp": "ja"}
        if lang in abbv:
            lang = abbv[lang]
        googletrans = GoogleTranslate(self.bot.session)
        res = await googletrans.translate(lang, "en", " ".join(txt))

        # Embed Build
        embed = discord.Embed(timestamp=ctx.message.created_at, colour=0x4A8AF4)
        embed.set_author(
            name="Google Translate", icon_url="https://translate.google.com/favicon.ico"
        )
        embed.add_field(name=f"Source [{res.source}]", value=res.origin, inline=False)
        embed.add_field(name=f"Translated [{res.dest}]", value=str(res), inline=False)
        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url
        )
        await ctx.send(embed=embed)

    @commands.command(usage="(project name)")
    async def pypi(self, ctx, project: str):
        """Get information of a python project from pypi."""
        async with self.bot.session.get(f"https://pypi.org/pypi/{project}/json") as res:
            try:
                res = await res.json()
            except aiohttp.client_exceptions.ContentTypeError:
                e = discord.Embed(
                    title="404 - Page Not Found",
                    description="We looked everywhere but couldn't find that project",
                    colour=discord.Colour(0x0073B7),
                )
                e.set_thumbnail(
                    url="https://cdn-images-1.medium.com/max/1200/1%2A2FrV8q6rPdz6w2ShV6y7bw.png"
                )
                return await ctx.reply(embed=e)

            info = res["info"]
            e = discord.Embed(
                title=f"{info['name']} · PyPI",
                description=info["summary"],
                colour=discord.Colour(0x0073B7),
            )
            e.set_thumbnail(
                url="https://cdn-images-1.medium.com/max/1200/1%2A2FrV8q6rPdz6w2ShV6y7bw.png"
            )
            e.add_field(
                name="Author Info",
                value=f"**Name**: {info['author']}\n"
                + f"**Email**: {info['author_email'] or '`Not provided.`'}",
            )
            e.add_field(name="Version", value=info["version"])
            e.add_field(
                name="Project Links",
                value="\n".join(
                    [f"[{x}]({y})" for x, y in dict(info["project_urls"]).items()]
                ),
            )
            e.add_field(name="License", value=info["license"] or "`Not specified.`")
            return await ctx.reply(embed=e)

    @commands.command(aliases=["searx", "g", "google"])
    async def search(self, ctx, *, keyword):
        """Search the web using searx."""
        if not ctx.channel.is_nsfw():
            return await ctx.send(
                "This command only available in NSFW chat since safe search is not available yet."
            )
        results = await self.searx.get_results(keyword)
        menu = menus.MenuPages(source=SearxResultsPageSource(ctx, results))
        await menu.start(ctx)


def setup(bot):
    bot.add_cog(Utils(bot))
