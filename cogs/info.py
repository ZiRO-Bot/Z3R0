import discord
import time

from cogs.api.weather import OpenWeatherAPI, CityNotFound
from cogs.utilities.embed_formatting import embedDefault, embedError
from discord.ext import commands
from typing import Union


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openweather = OpenWeatherAPI(
            self.bot.config["openweather_apikey"], session=self.bot.session
        )

    def is_weather():
        """Check if openweather api key exist."""

        def predicate(ctx):
            return ctx.bot.config["openweather_apikey"] is not None

        return commands.check(predicate)

    @commands.group(
        usage="(city)", invoke_without_command=True, example="{prefix}weather Palembang"
    )
    @is_weather()
    async def weather(self, ctx, *city):
        """Show weather report."""
        await ctx.invoke(self.bot.get_command("weather city"), *city)

    @weather.command(
        name="city", usage="(city)", example="{prefix}weather city Palembang"
    )
    async def weather_city(self, ctx, *city):
        """Show weather report from a city."""
        try:
            weatherData = await self.openweather.get_from_city(" ".join(city))
        except CityNotFound as err:
            e = embedError(err)
            return await ctx.reply(embed=e)
        e = embedDefault(
            ctx,
            title="{}, {}".format(weatherData.city, weatherData.country),
            description="Feels like {}°C, {}".format(
                weatherData.tempFeels.celcius, weatherData.weatherDetail
            ),
            color=discord.Colour(0xEA6D4A),
        )
        e.set_author(
            name="OpenWeather",
            icon_url="https://openweathermap.org/themes/openweathermap/assets/vendor/owm/img/icons/logo_60x60.png",
        )
        e.add_field(name="Temperature", value="{}°C".format(weatherData.temp.celcius))
        e.add_field(name="Humidity", value=weatherData.humidity)
        e.add_field(name="Wind", value=str(weatherData.wind))
        e.set_thumbnail(url=weatherData.iconUrl)
        await ctx.send(embed=e)

    @weather.command(
        name="zip", usage="(zip code)", example="{prefix}weather zip 10404"
    )
    async def weather_zip(self, ctx, _zip):
        """Show weather report from a zip code."""
        try:
            weatherData = await self.openweather.get_from_zip(_zip)
        except CityNotFound as err:
            e = embedError(err)
            return await ctx.reply(embed=e)
        e = embedDefault(
            ctx,
            title="{}, {}".format(weatherData.city, weatherData.country),
            description="Feels like {}°C, {}".format(
                weatherData.tempFeels.celcius, weatherData.weatherDetail
            ),
            color=discord.Colour(0xEA6D4A),
        )
        e.set_author(
            name="OpenWeather",
            icon_url="https://openweathermap.org/themes/openweathermap/assets/vendor/owm/img/icons/logo_60x60.png",
        )
        e.add_field(name="Temperature", value="{}°C".format(weatherData.temp.celcius))
        e.add_field(name="Humidity", value=weatherData.humidity)
        e.add_field(name="Wind", value=str(weatherData.wind))
        e.set_thumbnail(url=weatherData.iconUrl)
        await ctx.send(embed=e)

    @commands.command(aliases=["perms"])
    async def permissions(
        self, ctx, anyRoleMember: Union[discord.Member, discord.Role]
    ):
        """Get member/role's permission."""

        def format_text(text: str):
            return "`{}`".format(text.replace("_", " ").title())

        if isinstance(anyRoleMember, discord.Member):
            perms = {p[0]: p[1] for p in anyRoleMember.guild_permissions}
        if isinstance(anyRoleMember, discord.Role):
            perms = {p[0]: p[1] for p in anyRoleMember.permissions}

        if perms["administrator"]:
            perms = {"administrator": True}

        e = embedDefault(
            ctx,
            title="{}'s Permissions".format(anyRoleMember.name),
            colour=discord.Colour.rounded(),
        )
        if isinstance(anyRoleMember, discord.Member):
            e.set_thumbnail(url=anyRoleMember.avatar_url)
        e.add_field(
            name="Permissions",
            value=", ".join([format_text(perm) for perm in perms if perms[perm]]),
        )
        return await ctx.send(embed=e)

    @commands.command(aliases=["p"])
    async def ping(self, ctx):
        """Tell the ping of the bot to the discord servers."""
        start = time.perf_counter()
        e = discord.Embed(
            title="Pong!",
            timestamp=ctx.message.created_at,
            colour=discord.Colour(0xFFFFF0),
        )
        e.add_field(name="<a:loading:776255339716673566> | Websocket", value=f"{round(self.bot.latency*1000)}ms")
        e.set_footer(
            text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
        )
        msg = await ctx.send(embed=e)
        end = time.perf_counter()
        msg_ping = (end - start) * 1000
        e.add_field(name="<a:typing:785053882664878100> | Typing", value=f"{round(msg_ping)}ms", inline=False)
        await msg.edit(embed=e)

    @commands.command(aliases=["xi", "xboxuser", "xu"], usage="(gamertag)")
    async def xboxinfo(self, ctx, gamertag):
        """Show user's xbox information."""

        return await ctx.reply("`Sorry, This command is temporarily disabled due to technical difficulty.`")

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



def setup(bot):
    bot.add_cog(Info(bot))
