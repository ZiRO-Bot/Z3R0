import aiohttp
import asyncio
import core.bot as bot
import datetime
import discord
import epicstore_api
import json
import logging
import os
import platform
import re
import subprocess
import textwrap
import time

from cogs.utilities.formatting import bar_make, realtime
from cogs.utilities.embed_formatting import embedError
from discord.errors import Forbidden
from discord.ext import commands
from pytz import timezone
from typing import Optional, Union

egs = epicstore_api.EpicGamesStoreAPI()
session = aiohttp.ClientSession()

MORSE_CODE_DICT = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "0": "-----",
    ".": ".-.-.-",
    ", ": "--..--",
    "?": "..--..",
    "'": ".----.",
    "!": "-.-.--",
    "/": "-..-.",
    "-": "-....-",
    "(": "-.--.",
    ")": "-.--.-",
}


def encode(msg):
    morse = ""
    for letter in msg:
        if letter != " ":
            morse += MORSE_CODE_DICT[letter.upper()] + " "
        else:
            morse += "/ "
    return morse


def decode(msg):
    msg = msg.replace("/ ", " ") + " "
    temp = ""
    decoded = ""
    for code in msg:
        if code not in [".", "-", "/", " "] and code.upper() in list(
            MORSE_CODE_DICT.keys()
        ):
            return None
        if code != " ":
            i = 0
            temp += code
        else:
            i += 1
            if i == 2:
                decoded += " "
            else:
                decoded += list(MORSE_CODE_DICT.keys())[
                    list(MORSE_CODE_DICT.values()).index(temp)
                ]
                temp = ""
    return decoded


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("discord")
        self.weather_key = self.bot.config["openweather_apikey"]

    def is_weather():
        def predicate(ctx):
            if ctx.bot.config["openweather_apikey"]:
                return True

        return commands.check(predicate)

    def is_mod():
        def predicate(ctx):
            return ctx.author.guild_permissions.manage_channels

        return commands.check(predicate)

    def is_botmaster():
        def predicate(ctx):
            return ctx.author.id in ctx.bot.master

        return commands.check(predicate)

    @commands.command(usage="(language) (code)", brief="Compile code")
    async def compile(self, ctx, language=None, *, code=None):
        """Compile code from a variety of programming languages, powered by <https://wandbox.org/>\n\
           **Example**
           ``>compile python print('Hello World')``"""

        compilers = {
            "bash": "bash",
            "c": "gcc-head-c",
            "c#": "dotnetcore-head",
            "coffeescript": "coffescript-head",
            "cpp": "gcc-head",
            "elixir": "elixir-head",
            "go": "go-head",
            "java": "openjdk-head",
            "javascript": "nodejs-head",
            "lua": "lua-5.3.4",
            "perl": "perl-head",
            "php": "php-head",
            "python": "cpython-3.8.0",
            "ruby": "ruby-head",
            "rust": "rust-head",
            "sql": "sqlite-head",
            "swift": "swift-5.0.1",
            "typescript": "typescript-3.5.1",
            "vim-script": "vim-head",
        }
        if not language:
            await ctx.send(f"```json\n{json.dumps(compilers, indent=4)}```")
        if not code:
            await ctx.send("No code found")
            return
        try:
            compiler = compilers[language.lower()]
        except KeyError:
            await ctx.send("Language not found")
            return
        body = {"compiler": compiler, "code": code, "save": True}
        head = {"Content-Type": "application/json"}
        async with ctx.typing():
            async with self.bot.session.post(
                "https://wandbox.org/api/compile.json",
                headers=head,
                data=json.dumps(body),
            ) as r:
                # r = requests.post("https://wandbox.org/api/compile.json", headers=head, data=json.dumps(body))
                try:
                    response = json.loads(await r.text())
                    # await ctx.send(f"```json\n{json.dumps(response, indent=4)}```")
                    self.logger.info(f"json\n{json.dumps(response, indent=4)}")
                except json.decoder.JSONDecodeError:
                    self.logger.error(f"json\n{r.text}")
                    await ctx.send(f"```json\n{r.text}```")

                try:
                    embed = discord.Embed(title="Compiled code")
                    embed.add_field(
                        name="Output",
                        value=f'```{response["program_message"]}```',
                        inline=False,
                    )
                    embed.add_field(
                        name="Exit code", value=response["status"], inline=True
                    )
                    embed.add_field(
                        name="Link",
                        value=f"[Permalink]({response['url']})",
                        inline=True,
                    )
                    await ctx.send(embed=embed)
                except KeyError:
                    self.logger.error(f"json\n{json.dumps(response, indent=4)}")
                    await ctx.send(f"```json\n{json.dumps(response, indent=4)}```")

    @commands.command()
    async def source(self, ctx):
        """Show link to ziBot's source code."""
        git_link = "https://github.com/null2264/ziBot"
        await ctx.send(f"ziBot's source code: \n{git_link}")

    @commands.command(aliases=["ui"], usage="[member]")
    async def userinfo(self, ctx, *, user: Union[discord.Member, discord.User] = None):
        """Show user information."""
        member = user or ctx.message.author

        def stat(x):
            return {
                "offline": "<:status_offline:747799247243575469>",
                "idle": "<:status_idle:747799258316668948>",
                "dnd": "<:status_dnd:747799292592259204>",
                "online": "<:status_online:747799234828435587>",
                "streaming": "<:status_streaming:747799228054765599>",
            }.get(str(x), "None")

        def badge(x):
            return {
                "UserFlags.hypesquad_balance": "<:balance:747802468586356736>",
                "UserFlags.hypesquad_brilliance": "<:brilliance:747802490241810443>",
                "UserFlags.hypesquad_bravery": "<:bravery:747802479533490238>",
                "UserFlags.bug_hunter": "<:bughunter:747802510663745628>",
                "UserFlags.booster": "<:booster:747802502677659668>",
                "UserFlags.hypesquad": "<:hypesquad:747802519085776917>",
                "UserFlags.partner": "<:partner:747802528594526218>",
                "UserFlags.owner": "<:owner:747802537402564758>",
                "UserFlags.staff": "<:stafftools:747802548391379064>",
                "UserFlags.early_supporter": "<:earlysupport:747802555689730150>",
                "UserFlags.verified": "<:verified:747802457798869084>",
                "UserFlags.verified_bot": "<:verified:747802457798869084>",
                "UserFlags.verified_bot_developer": "<:verified_bot_developer:748090768237002792>",
            }.get(x, "🚫")

        def activity(x):
            return {
                "playing": "Playing ",
                "watching": "Watching ",
                "listening": "Listening to ",
                "streaming": "Streaming ",
                "custom": "",
            }.get(x, "None ")

        badges = []
        for x in list(member.public_flags.all()):
            x = str(x)
            if member == ctx.guild.owner:
                badges.append(badge("UserFlags.owner"))
            badges.append(badge(x))

        if isinstance(member, discord.Member):
            roles = [role.mention for role in member.roles if role.name != "@everyone"]

        jakarta = timezone("Asia/Jakarta")

        if isinstance(member, discord.Member):
            status = member.status
            statEmoji = stat(member.status)
        else:
            status = "Unknown"
            statEmoji = "❓"
        embed = discord.Embed(
            description=f"{statEmoji}({status})\n"
            + (
                "<:activity:748091280227041281>"
                + activity(str(member.activity.type).replace("ActivityType.", ""))
                + f"**{member.activity.name}**"
                if isinstance(member, discord.Member) and member.activity
                else ""
            ),
            colour=member.colour if member else discord.Colour(0x000000),
            timestamp=ctx.message.created_at,
        )
        embed.set_author(name=f"{member}", icon_url=member.avatar_url)
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Guild name", value=member.display_name)
        embed.add_field(
            name="Badges", value=" ".join(badges) if badges else "No badge."
        )
        embed.add_field(
            name="Created on",
            value=member.created_at.replace(tzinfo=timezone("UTC"))
            .astimezone(jakarta)
            .strftime("%a, %#d %B %Y, %H:%M WIB"),
        )
        embed.add_field(
            name="Joined on",
            value=member.joined_at.replace(tzinfo=timezone("UTC"))
            .astimezone(jakarta)
            .strftime("%a, %#d %B %Y, %H:%M WIB")
            if isinstance(member, discord.Member)
            else "Not in this server.",
        )
        if isinstance(member, discord.Member):
            if len(", ".join(roles)) <= 1024:
                embed.add_field(
                    name=f"Roles ({len(roles)})",
                    value=", ".join(roles) or "No roles.",
                    inline=False,
                )
            else:
                embed.add_field(name=f"Roles", value=f"{len(roles)}", inline=False)
        embed.set_footer(
            text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["si"])
    async def serverinfo(self, ctx):
        """Show server information."""
        embed = discord.Embed(
            title=f"About {ctx.guild.name}",
            colour=discord.Colour(0xFFFFF0),
            timestamp=ctx.message.created_at,
        )

        roles = []
        for role in ctx.guild.roles:
            if role.name != "@everyone":
                roles.append(role.mention)
        width = 3

        boosters = [x.mention for x in ctx.guild.premium_subscribers]

        embed.add_field(name="Owner", value=f"{ctx.guild.owner.mention}", inline=False)
        embed.add_field(name="Created on", value=f"{ctx.guild.created_at.date()}")
        embed.add_field(name="Region", value=f"``{ctx.guild.region}``")
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.add_field(
            name="Verification Level", value=f"{ctx.guild.verification_level}".title()
        )
        embed.add_field(
            name="Channels",
            value="<:categories:747750884577902653>"
            + f" {len(ctx.guild.categories)}\n"
            + "<:text_channel:747744994101690408>"
            + f" {len(ctx.guild.text_channels)}\n"
            + "<:voice_channel:747745006697185333>"
            + f" {len(ctx.guild.voice_channels)}",
        )
        embed.add_field(name="Members", value=f"{ctx.guild.member_count}")
        if len(boosters) < 5:
            embed.add_field(
                name=f"Boosters ({len(boosters)})",
                value=",\n".join(
                    ", ".join(boosters[i : i + width])
                    for i in range(0, len(boosters), width)
                )
                if boosters
                else "No booster.",
            )
        else:
            embed.add_field(name=f"Boosters ({len(boosters)})", value=len(boosters))
        if len(", ".join(roles)) <= 1024:
            embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles))
        else:
            embed.add_field(name=f"Roles", value=f"{len(roles)}")
        embed.set_footer(text=f"ID: {ctx.guild.id}")
        await ctx.send(embed=embed)

    @commands.command()
    async def invite(self, ctx):
        """Get bot's invite link."""
        e = discord.Embed(
            title="Want to invite ziBot?",
            description="[Invite with administrator permission]("
            + discord.utils.oauth_url(
                self.bot.user.id,
                permissions=discord.Permissions(8),
                guild=None,
                redirect_uri=None,
            )
            + ")\n"
            + "[Invite with necessary premissions ***recommended**]("
            + discord.utils.oauth_url(
                self.bot.user.id,
                permissions=discord.Permissions(1879571542),
                guild=None,
                redirect_uri=None,
            )
            + ")\n"
            + "[Invite with no permissions]("
            + discord.utils.oauth_url(
                self.bot.user.id, permissions=None, guild=None, redirect_uri=None
            )
            + ")\n",
            colour=discord.Colour(0xFFFFF0),
        )
        await ctx.send(embed=e)

    @commands.command(aliases=["bi", "about", "info", "uptime", "up"])
    async def botinfo(self, ctx):
        """Show bot information."""
        start = time.perf_counter()
        invite_link = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=discord.Permissions(1879571542),
            guild=None,
            redirect_uri=None,
        )
        embed = discord.Embed(
            title="About ziBot",
            colour=discord.Colour(0xFFFFF0),
            timestamp=ctx.message.created_at,
        )
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(name="Author", value="ZiRO2264#4572")
        embed.add_field(
            name="Python",
            value=f"[{platform.python_version()}](https://www.python.org)",
        )
        embed.add_field(
            name="discord.py",
            value=f"[{discord.__version__}-modified](https://github.com/null2264/discord.py)",
        )
        embed.add_field(
            name="Links",
            value=f"[Invite]({invite_link})\n"
            + "[Donate](https://www.patreon.com/ziro2264)\n"
            + "[GitHub Repo](https://github.com/null2264/ziBot)\n"
            + "[Documentation](https://ziro-bot.github.io)\n"
            + "[Support Server](https://discord.gg/sP9xRy6)\n",
        )
        embed.add_field(
            name="Stats",
            value=f"**Uptime**: {realtime(int(time.time() - bot.start_time))}\n**Servers**: {len(self.bot.guilds)}",
        )
        embed.add_field(
            name="License",
            value="[GNU GPL-3.0-or-later](https://github.com/null2264/ziBot/blob/master/LICENSE)",
        )
        embed.add_field(
            name="About",
            value="**ziBot** is an open source bot, "
            + "a fork of [mcbeDiscordBot](https://github.com/AnInternetTroll/mcbeDiscordBot) "
            + "(Steve the Bot) created by [AnInternetTroll](https://github.com/AnInternetTroll), "
            + f"but rewritten a bit.\n\n**Bot Version**: {ctx.bot.version}",
            inline=False,
        )
        embed.set_footer(
            text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["spi", "spot", "spotify"], usage="[member]")
    async def spotifyinfo(self, ctx, *, user: discord.Member = None):
        """Show member's spotify information."""
        user = user or ctx.message.author
        if spotify := discord.utils.find(
            lambda a: isinstance(a, discord.Spotify), user.activities
        ):
            offset = 54  # Sometime it wont line up on some server, this is the only solution i could come up with
            (
                duration,
                current,
            ) = spotify.duration, datetime.datetime.utcnow() - spotify.start + datetime.timedelta(
                seconds=offset
            )
            percentage = int(round(float(f"{current/duration:.2%}".replace("%", ""))))
            bar_length = 5 if user.is_on_mobile() else 17
            bar = bar_make(
                current.seconds,
                spotify.duration.seconds,
                fill="⬤",
                empty="─",
                point=True,
                length=bar_length,
            )
            artists = ", ".join(spotify.artists)

            embed = discord.Embed(
                title=f"{spotify.title}",
                colour=spotify.colour,
                timestamp=ctx.message.created_at,
            )
            embed.set_author(name="Spotify", icon_url="https://i.imgur.com/PA3vvdN.png")
            embed.set_thumbnail(url=spotify.album_cover_url)
            embed.add_field(name="Artist", value=artists)
            embed.add_field(name="Album", value=spotify.album)
            embed.add_field(
                name="Duration",
                value=f"{current.seconds//60:02}:{current.seconds%60:02}"
                + f" {bar} "
                + f"{duration.seconds//60:02}:"
                + f"{duration.seconds%60:02}",
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error!",
                description=f"{user.mention} is not listening to Spotify!",
                colour=discord.Colour(0x2F3136),
            )
            await ctx.send(embed=embed)

    @commands.command(usage="(words)", example="{prefix}morse SOS")
    async def morse(self, ctx, *msg):
        """Encode message into morse code."""
        encoded = encode(" ".join([*msg]))
        if not encoded:
            return
        e = discord.Embed(
            title=f"{ctx.author.name}#{ctx.author.discriminator}",
            description=encoded,
        )
        await ctx.send(embed=e)

    @commands.command(
        usage="(morse code)", aliases=["demorse"], example="{prefix}unmorse ... --- ..."
    )
    async def unmorse(self, ctx, *msg):
        """Decode morse code."""
        decoded = decode(str(" ".join([*msg])))
        if decoded is None:
            await ctx.send(f"{' '.join([*msg])} is not a morse code!")
            return
        e = discord.Embed(
            title=f"{ctx.author.name}#{ctx.author.discriminator}", description=decoded
        )
        await ctx.send(embed=e)

    @commands.command(usage="(country)")
    async def covid(self, ctx, *country):
        """Show covid information on certain country."""
        country = " ".join([*country])
        if country.lower() in ["united state of america", "america"]:
            country = "USA"
        if country.lower() in ["united kingdom"]:
            country = "UK"
        api = "https://api.covid19api.com/total/country"
        async with session.get(f"{api}/{country}") as url:
            try:
                covData = json.loads(await url.text())
            except json.decoder.JSONDecodeError:
                e = embedError(f"502 Bad Gateway, please try again later.")
                await ctx.send(embed=e)
                return
                
            try:
                covData = covData[len(covData) - 1]
            except KeyError:
                e = embedError(f"{country} not found")
                await ctx.send(embed=e)
                return
        e = discord.Embed(title=covData["Country"], timestamp=ctx.message.created_at)
        e.add_field(name="Active", value=f"{covData['Active']:,}")
        e.add_field(name="Recovered", value=f"{covData['Recovered']:,}")
        e.add_field(name="Deaths", value=f"{covData['Deaths']:,}")
        e.add_field(name="Confirmed Cases", value=f"{covData['Confirmed']:,}")
        e.set_footer(
            text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
        )
        await ctx.send(embed=e)

    @commands.group(aliases=["egs"])
    async def epicgames(self, ctx):
        """Get information from epic games store."""
        pass

    @epicgames.command(name="games")
    async def _games(self, ctx, *keywords):
        keywords = " ".join([*keywords])
        catalog = egs.fetch_catalog(product_type="games", keywords=keywords)["data"][
            "Catalog"
        ]["catalogOffers"]["elements"]
        totalPage = len(catalog)
        currentPage = 1
        embed_reactions = ["◀️", "▶️", "⏹️"]

        def check_reactions(reaction, user):
            if user == ctx.author and str(reaction.emoji) in embed_reactions:
                return str(reaction.emoji)
            else:
                return False

        def create_embed(ctx, data, page):
            try:
                data = data[page - 1]
            except IndexError:
                return None
            # EGS haven't implemented rating system yet.
            rating = "🤔 -"

            publisherName = None
            developerName = None
            for i in range(len(data["linkedOffer"]["customAttributes"])):
                if data["linkedOffer"]["customAttributes"][i]["key"] == "publisherName":
                    publisherName = data["linkedOffer"]["customAttributes"][i]["value"]
                elif (
                    data["linkedOffer"]["customAttributes"][i]["key"] == "developerName"
                ):
                    developerName = data["linkedOffer"]["customAttributes"][i]["value"]

            price = data["price"]["totalPrice"]["fmtPrice"]["originalPrice"]
            discountPrice = data["price"]["totalPrice"]["fmtPrice"]["discountPrice"]
            fmtPrice = price if price != "0" else "Free"
            if discountPrice != "0" and price != discountPrice:
                fmtPrice = f"~~{price if price != '0' else 'Free'}~~ {discountPrice}"

            imageTall = None
            imageWide = None
            for i in range(len(data["keyImages"])):
                if data["keyImages"][i]["type"] == "DieselStoreFrontWide":
                    imageWide = data["keyImages"][i]["url"]
                elif data["keyImages"][i]["type"] == "DieselStoreFrontTall":
                    imageTall = data["keyImages"][i]["url"]

            embed = discord.Embed(
                title=data["title"],
                url=f"https://www.epicgames.com/store/en-US/product/{data['urlSlug']}",
                color=discord.Colour(0x303030),
            )
            embed.set_author(
                name=f"Epic Games Store - Page {currentPage}/{totalPage} - {rating}%",
                icon_url="https://raw.githubusercontent.com/null2264/null2264/master/egs.png",
            )
            embed.set_thumbnail(url=imageTall)
            embed.set_image(url=imageWide)
            embed.add_field(
                name="Developer", value=developerName or publisherName or "-"
            )
            embed.add_field(
                name="Publisher", value=publisherName or developerName or "-"
            )
            embed.add_field(name="Price", value=fmtPrice)
            return embed

        e = create_embed(ctx, catalog, currentPage)
        if not e:
            await ctx.send(f"Can't find any games with keywords `{keywords}`")
            return
        msg = await ctx.send(embed=e)
        for emoji in embed_reactions:
            await msg.add_reaction(emoji)
        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=check_reactions, timeout=60.0
                )
            except asyncio.TimeoutError:
                break
            else:
                emoji = check_reactions(reaction, user)
                try:
                    await msg.remove_reaction(reaction.emoji, user)
                except discord.Forbidden:
                    pass
                if emoji == "◀️" and currentPage != 1:
                    currentPage -= 1
                    e = create_embed(ctx, catalog, currentPage)
                    await msg.edit(embed=e)
                if emoji == "▶️" and currentPage != totalPage:
                    currentPage += 1
                    e = create_embed(ctx, catalog, currentPage)
                    await msg.edit(embed=e)
                if emoji == "⏹️":
                    # await msg.clear_reactions()
                    break
        return

    @commands.command(aliases=["userpfp"], usage="[member]")
    async def avatar(self, ctx, member: discord.User = None):
        """Show member's avatar image."""
        if not member:
            member = ctx.author
        e = discord.Embed(
            title="Avatar",
            colour=discord.Colour(0xFFFFF0),
            description=f"[jpeg]({member.avatar_url_as(format='jpg')}) | [png]({member.avatar_url_as(format='png')}) | [webp]({member.avatar_url_as(format='webp')}) "
            + (
                f"| [gif]({member.avatar_url_as(format='gif')})"
                if member.is_avatar_animated()
                else ""
            ),
        )
        e.set_image(url=member.avatar_url_as(size=1024))
        e.set_author(name=member, icon_url=member.avatar_url)
        await ctx.send(embed=e)

    def isRafael():
        async def pred(ctx):
            return ctx.author.id == 518154918276628490

        return commands.check(pred)

    @commands.command(name="find-waifu")
    @isRafael()
    async def findwaifu(self, ctx):
        """Rafael and his waifu."""
        f = discord.File("./assets/img/rafaelAndHisWaifu.png", filename="img.png")
        return await ctx.send(file=f)


def setup(bot):
    bot.add_cog(General(bot))
