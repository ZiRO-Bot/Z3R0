"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import datetime
import discord
import time


from api.openweather import OpenWeatherAPI, CityNotFound
from core.mixin import CogMixin
from exts.utils import pillow
from exts.utils.format import ZEmbed
from exts.utils.infoQuote import *
from discord.ext import commands
from typing import Union


# TODO: Move this somewhere in `exts/utils/` folder
async def authorOrReferenced(ctx):
    if ctx.message and (ref := ctx.message.reference):
        # Get referenced message author
        # if user reply to a message while doing this command
        return (
            ref.cached_message.author
            if ref.cached_message
            else (await ctx.fetch_message(ref.message_id)).author
        )
    return ctx.author


class Info(commands.Cog, CogMixin):
    """Commands that gives you information."""

    icon = "<:info:783206485051441192>"

    def __init__(self, bot):
        super().__init__(bot)
        self.openweather = OpenWeatherAPI(
            key=getattr(self.bot.config, "openweather", None), session=self.bot.session
        )

    @commands.command(aliases=["p"])
    async def ping(self, ctx):
        """Get bot's response time"""
        start = time.perf_counter()
        e = ZEmbed.default(ctx, title="Pong!")
        e.add_field(
            name="<a:loading:776255339716673566> | Websocket",
            value=f"{round(self.bot.latency*1000)}ms",
        )
        msg = await ctx.try_reply(embed=e)
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
        """Get member's avatar image"""
        if not user:
            user = await authorOrReferenced(ctx)

        # Embed stuff
        e = ZEmbed.default(
            ctx,
            title="{}'s Avatar".format(user.name),
            description="[`JPEG`]({})".format(user.avatar_url_as(format="jpg"))
            + " | [`PNG`]({})".format(user.avatar_url_as(format="png"))
            + " | [`WEBP`]({})".format(user.avatar_url_as(format="webp"))
            + (
                " | [`GIF`]({})".format(user.avatar_url_as(format="gif"))
                if user.is_avatar_animated()
                else ""
            ),
        )
        e.set_image(url=user.avatar_url_as(size=1024))
        await ctx.try_reply(embed=e)

    @commands.command(aliases=["w"])
    async def weather(self, ctx, *, city):
        """Get current weather on specific city"""
        if not self.openweather.apiKey:
            # TODO: Adjust error message
            return await ctx.send(
                "OpenWeather's API Key is not set! Please contact the bot owner to solve this issue."
            )

        try:
            weatherData = await self.openweather.get_from_city(city)
        except CityNotFound as err:
            # TODO: Also adjust this message
            return await ctx.try_reply("City not Found!")

        e = ZEmbed(
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
        await ctx.try_reply(embed=e)

    @commands.command(aliases=["clr", "color"])
    async def colour(self, ctx, value: str):
        """Get colour information from hex value"""
        # Pre processing
        value = value.lstrip("#")[:6]
        value = value.ljust(6, "0")

        try:
            h = str(hex(int(value, 16)))[2:]
            h = h.ljust(6, "0")
        except ValueError:
            return await ctx.send("Invalid colour value!")
        # Convert HEX into RGB
        RGB = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

        image = await pillow.rectangle(*RGB)
        f = discord.File(fp=image, filename="rect.png")
        
        e = ZEmbed.default(
            ctx,
            title="Information on #{}".format(h),
            colour=discord.Colour(int(h, 16) if h != "ffffff" else 0xFFFFF0),
        )
        e.set_thumbnail(url="attachment://rect.png")
        e.add_field(name="Hex", value=f"#{h}")
        e.add_field(name="RGB", value=str(RGB))
        return await ctx.try_reply(file=f, embed=e)

    @commands.command(aliases=["lvl", "rank"], hidden=True)
    async def level(self, ctx):
        """Level"""
        return await ctx.try_reply("https://tenor.com/view/stop-it-get-some-help-gif-7929301")


def setup(bot):
    bot.add_cog(Info(bot))
