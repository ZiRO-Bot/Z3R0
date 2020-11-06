import aiohttp
import asyncio
import bot
import discord
import epicstore_api
import json
import platform
import textwrap
import time

from .errors.weather import CityNotFound
from .utilities.formatting import bar_make, realtime
from discord.ext import commands
from pytz import timezone

egs = epicstore_api.EpicGamesStoreAPI()
session = aiohttp.ClientSession()

def temperature(temp, unit: str, number_only=False):
    if unit == "c":
        temp = temp - 273.15
    elif unit == "f":
        temp = (temp - 273.15) * 1.8 + 32
    if number_only:
        return f"{round(temp)}"
    return f"{round(temp)}°{unit.upper()}"

async def get_weather_data(key, *place: str, _type="city"):
    place = " ".join([*place])
    if _type == "city":
        q = "q"
    elif _type == "zip":
        q = "zip"
    apilink = f"https://api.openweathermap.org/data/2.5/weather?{q}={place}&appid={key}"
    async with session.get(apilink) as url:
        weatherData = json.loads(await url.text())
        if weatherData["cod"] == "404":
            raise CityNotFound
        return weatherData

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weather_apikey = self.bot.config.openweather_apikey
    
    def is_weather():
        def predicate(ctx):
            if ctx.bot.config.openweather_apikey:
                return True

        return commands.check(predicate)
    
    @commands.command(aliases=["ui"], usage="[member]")
    async def userinfo(self, ctx, *, user: discord.Member = None):
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

        roles = []
        if member:
            for role in member.roles:
                if role.name != "@everyone":
                    roles.append(role.mention)

        jakarta = timezone("Asia/Jakarta")

        if member:
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
                if member and member.activity
                else ""
            ),
            colour=member.colour if member else discord.Colour(0x000000),
            timestamp=ctx.message.created_at,
        )
        embed.set_author(
            name=f"{member}", icon_url=member.avatar_url
        )
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
            if member
            else "Not a member.",
        )
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

    @commands.command(aliases=["bi", "about", "uptime", "up", "invite"])
    async def botinfo(self, ctx):
        """Show bot information."""
        bot_ver = "2.1.S"
        start = time.perf_counter()
        invite_link = discord.utils.oauth_url(
            self.bot.user.id, permissions=None, guild=None, redirect_uri=None
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
            value=f"[Invitation]({invite_link})\n"
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
            + f"but rewritten a bit.\n\n**Bot Version**: {bot_ver}",
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
            offset = 27  # Sometime it wont line up on some server, this is the only solution i could come up with
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

    @commands.command(aliases=["xi", "xboxuser", "xu"], usage="(gamertag)")
    async def xboxinfo(self, ctx, gamertag):
        """Show user's xbox information."""
        xbox = "https://xbl-api.prouser123.me/profile/gamertag"
        async with session.get(f"{xbox}/{gamertag}") as url:
            xboxdata = json.loads(await url.text())["profileUsers"][0]["settings"]
        if not xboxdata:
            return

        _gamertag = xboxdata[4]["value"]
        gamerscore = xboxdata[3]["value"]
        tier = xboxdata[6]["value"]
        reputation = xboxdata[8]["value"]

        e = discord.Embed(
            title=_gamertag,
            color=discord.Colour(0x107C10),
            timestamp=ctx.message.created_at,
        )
        e.set_author(
            name="Xbox",
            icon_url="https://raw.githubusercontent.com/null2264/null2264/master/xbox.png",
        )
        e.set_thumbnail(url=xboxdata[5]["value"])
        e.add_field(
            name="Gamerscore", value=f"<:gamerscore:752423525247352884>{gamerscore}"
        )
        e.add_field(name="Account Tier", value=tier)
        e.add_field(name="Reputation", value=reputation)
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
    
    @commands.command()
    async def source(self, ctx):
        """Show link to ziBot's source code."""
        git_link = "https://github.com/null2264/ziBot"
        await ctx.send(f"ziBot's source code: \n{git_link}")
    
    @commands.group(
        usage="(city)", invoke_without_command=True, example="{prefix}weather Palembang"
    )
    @is_weather()
    async def weather(self, ctx, *city):
        """Show weather report."""
        await ctx.invoke(self.bot.get_command(f"weather city"), *city)

    @weather.command(
        name="city", usage="(city)", example="{prefix}weather city Palembang"
    )
    async def weather_city(self, ctx, *city):
        """Show weather report from a city."""
        try:
            weatherData = await get_weather_data(self.weather_apikey, *city, _type="city")
        except CityNotFound:
            await ctx.send("City not found")
            return
        temp = temperature(weatherData["main"]["temp"], "c")
        feels_like = temperature(weatherData["main"]["feels_like"], "c")
        e = discord.Embed(
            title=f"{weatherData['name']}, {weatherData['sys']['country']}",
            description=f"Feels like {feels_like}. {weatherData['weather'][0]['description'].title()}",
            color=discord.Colour(0xEA6D4A),
            timestamp=ctx.message.created_at,
        )
        e.set_thumbnail(
            url=f"https://openweathermap.org/img/wn/{weatherData['weather'][0]['icon']}@2x.png"
        )
        e.set_author(
            name="OpenWeather",
            icon_url="https://openweathermap.org/themes/openweathermap/assets/vendor/owm/img/icons/logo_60x60.png",
        )
        e.add_field(name="Temperature", value=temp)
        e.add_field(name="Humidity", value=f"{weatherData['main']['humidity']}%")
        e.add_field(name="Wind", value=f"{weatherData['wind']['speed']}m/s")
        e.set_footer(
            text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
        )
        await ctx.send(embed=e)

    @weather.command(
        name="zip", usage="(zip code)", example="{prefix}weather zip 10404"
    )
    async def weather_zip(self, ctx, *city):
        """Show weather report from a zip code."""
        try:
            weatherData = await get_weather_data(self.weather_apikey, *city, _type="city")
        except CityNotFound:
            await ctx.send("City not found")
            return
        temp = temperature(weatherData["main"]["temp"], "c")
        feels_like = temperature(weatherData["main"]["feels_like"], "c")
        e = discord.Embed(
            title=f"{weatherData['name']}, {weatherData['sys']['country']}",
            description=f"Feels like {feels_like}. {weatherData['weather'][0]['description'].title()}",
            color=discord.Colour(0xEA6D4A),
            timestamp=ctx.message.created_at,
        )
        e.set_thumbnail(
            url=f"https://openweathermap.org/img/wn/{weatherData['weather'][0]['icon']}@2x.png"
        )
        e.set_author(
            name="OpenWeather",
            icon_url="https://openweathermap.org/themes/openweathermap/assets/vendor/owm/img/icons/logo_60x60.png",
        )
        e.add_field(name="Temperature", value=temp)
        e.add_field(name="Humidity", value=f"{weatherData['main']['humidity']}%")
        e.add_field(name="Wind", value=f"{weatherData['wind']['speed']}m/s")
        e.set_footer(
            text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
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
            covData = json.loads(await url.text())
        try:
            covData = covData[len(covData) - 1]
        except KeyError:
            await ctx.send(f"{country} not found")
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
    

def setup(bot):
    bot.add_cog(Info(bot))
