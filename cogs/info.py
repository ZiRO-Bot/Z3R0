import aiohttp
import asyncio
import core.bot as bot
import datetime
import discord
import epicstore_api
import json
import platform
import textwrap
import time

from .errors.weather import CityNotFound, PlaceParamEmpty
from .utils.api.pokeapi import PokeAPI
from .utils.formatting import bar_make, realtime, general_time
from discord.ext import commands, menus
from pytz import timezone

egs = epicstore_api.EpicGamesStoreAPI()
session = aiohttp.ClientSession()


class PokedexMenu(menus.Menu):
    def __init__(self, data, message):
        super().__init__(timeout=30.0, delete_message_after=False)
        self.message = message
        self.data = data
        self.status = 200 if "Not Found" not in self.data else 404
        self.current_page = None

    async def start(self, ctx, *, channel=None, wait=False):
        await super().start(ctx)
        if self.status == 200:
            await self.show_page("home")
            return
            # return await self.message.edit(await self.show_page("home"))
        e = discord.Embed(title="404 Not Found", colour=discord.Colour.red())
        return await self.message.edit(embed=e)

    def should_add_reactions(self):
        return self.status == 200

    def format(self, data):
        e = discord.Embed(title=f"#{data['id']} - {data['name'].title()}", description=data['text'], colour=discord.Colour.red())
        try:
            e.set_thumbnail(url=data['sprites']['frontDefault'])
        except KeyError:
            pass
        return e

    async def show_page(self, page):
        if self.current_page == page:
            return
        e = self.format(self.data)
        data = self.data
        if page == "home":
            types = " ".join([f"`{x.upper()}`" for x in data["types"]])
            height = round(data["height"] * 0.32808)
            weight = round((data["weight"]/10) / 0.45359237, 1)
            e.add_field(name="Height", value=f"{height}'")
            e.add_field(name="Weight", value=f"{weight} lbs")
            e.add_field(name=f"Type{'s' if len(types) > 1 else ''}", value=types)
        elif page == "stats":
            e.add_field(name="HP", value="0")
        self.current_page = page
        return await self.message.edit(embed=e)
    
    @menus.button('🏠', position=menus.First(0))
    async def go_to_home(self, payload):
        # if self.current_page != "home":
        return await self.show_page("home")
    
    @menus.button('📋', position=menus.First(1))
    async def go_to_stats(self, payload):
        # if self.current_page != "stats":
        return await self.show_page("stats")


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
    if not place:
        raise PlaceParamEmpty
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
        self.pokeapi = PokeAPI(self.bot.session)
        try:
            self.weather_apikey = self.bot.config.openweather_apikey
        except AttributeError:
            self.weather_apikey = None

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
            + "[Invite with necessary premissions (**recommended**)]("
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

    def get_bot_uptime(self):
        return general_time(
            self.bot.start_time, accuracy=None, brief=True, suffix=False
        )

    @commands.command(aliases=["bi", "about", "info", "uptime", "up"])
    async def botinfo(self, ctx):
        """Show bot information."""
        bot_ver = "3.0.R"
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
            value=f"**Uptime**: {self.get_bot_uptime()}\n**Servers**: {len(self.bot.guilds)}",
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
            weatherData = await get_weather_data(
                self.weather_apikey, *city, _type="city"
            )
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
            weatherData = await get_weather_data(
                self.weather_apikey, *city, _type="city"
            )
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

    @commands.command()
    async def license(self, ctx):
        """Show bot's license."""
        _license = (
            "ziBot is a multi-purpose, customizable, open-source discord bot.\n"
            + "Copyright (C) 2020  Ahmad Ansori Palembani\n\n"
            + "This program is free software: you can redistribute it and/or modify"
            + "it under the terms of the GNU General Public License as published by"
            + "the Free Software Foundation, either version 3 of the License, or"
            + "(at your option) any later version.\n\n"
            + "This program is distributed in the hope that it will be useful,"
            + "but WITHOUT ANY WARRANTY; without even the implied warranty of"
            + "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the"
            + "GNU General Public License for more details.\n\n"
            + "You should have received a copy of the GNU General Public License"
            + "along with this program.  If not, see <https://www.gnu.org/licenses/>."
        )
        e = discord.Embed(
            title="License",
            colour=discord.Colour(0xFFFFF0),
            description=f"**GNU GPL-3.0-or-Later**\n```{_license}```",
        )
        await ctx.send(embed=e)

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
    
    @commands.command(aliases=["p"])
    async def ping(self, ctx):
        """Tell the ping of the bot to the discord servers."""
        start = time.perf_counter()
        e = discord.Embed(
            title="Pong!",
            timestamp=ctx.message.created_at,
            colour=discord.Colour(0xFFFFF0),
        )
        e.add_field(name="<:zibot:785055470401749032> | Websocket", value=f"`{round(self.bot.latency*1000, 2)}` ms")
        db_start = time.perf_counter()
        async with ctx.db.acquire() as conn:
            await conn.fetch("""SELECT * FROM guilds""")
            db_end = time.perf_counter()
        db_ping = (db_end - db_start) * 1000
        e.add_field(name="<:psql:785055943209123900> | Database", value=f"`{round(db_ping, 2)}` ms")
        e.set_footer(
            text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
        )
        msg = await ctx.send(embed=e)
        end = time.perf_counter()
        msg_ping = (end - start) * 1000
        e.add_field(name="<a:typing:785053882664878100> | Typing", value=f"`{round(msg_ping, 2)}` ms")
        await msg.edit(embed=e)

    @commands.command()
    async def pokedex(self, ctx, pokemon):
        """Get pokedex entry of a pokemon."""
        msg = await ctx.reply(embed=discord.Embed(title="<a:loading:776255339716673566> Getting pokemon info...", colour=discord.Colour.red()))
        req = await self.pokeapi.get_pokemon(pokemon=pokemon)
        menus = PokedexMenu(req, msg)
        await menus.start(ctx)
        # if "Not Found" in req:
        #     e = discord.Embed(title="404 Not Found", colour=discord.Colour.red())
        # else:
        #     types = " ".join([f"`{x.upper()}`" for x in req["types"]])
        #     height = round(req["height"] * 0.32808)
        #     weight = round((req["weight"]/10) / 0.45359237, 1)
        #     e = discord.Embed(title=f"#{req['id']} - {req['name'].title()}", description=req['text'], colour=discord.Colour.red())
        #     e.add_field(name="Height", value=f"{height}'")
        #     e.add_field(name="Weight", value=f"{weight} lbs")
        #     e.add_field(name=f"Type{'s' if len(types) > 1 else ''}", value=types)
        #     try:
        #         e.set_thumbnail(url=req['sprites']['frontDefault'])
        #     except KeyError:
        #         pass
        # await msg.edit(embed=e)


def setup(bot):
    bot.add_cog(Info(bot))
