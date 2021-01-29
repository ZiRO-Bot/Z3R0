import discord

from cogs.api.weather import OpenWeatherAPI, CityNotFound
from cogs.utilities.embed_formatting import embedDefault, embedError
from discord.ext import commands


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openweather = OpenWeatherAPI(self.bot.config["openweather_apikey"], session=self.bot.session)

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
            description="Feels like {}°C, {}".format(weatherData.tempFeels.celcius, weatherData.weatherDetail),
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
            description="Feels like {}°C, {}".format(weatherData.tempFeels.celcius, weatherData.weatherDetail),
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

def setup(bot):
    bot.add_cog(Info(bot))
