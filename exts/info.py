"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import datetime
import discord
import time
import unicodedata


from api.openweather import OpenWeatherAPI, CityNotFound
from core import checks
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
    cc = True

    def __init__(self, bot):
        super().__init__(bot)
        self.openweather = OpenWeatherAPI(
            key=getattr(self.bot.config, "openweather", None), session=self.bot.session
        )

    @commands.command(aliases=["p"], brief="Get bot's response time")
    async def ping(self, ctx):
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

    @commands.command(
        aliases=["av", "userpfp", "pfp"], brief="Get member's avatar image"
    )
    async def avatar(self, ctx, user: discord.User = None):
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

    @commands.command(
        aliases=["w"],
        brief="Get current weather for specific city",
        example=("weather Palembang", "w London"),
    )
    async def weather(self, ctx, *, city):
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
            colour=discord.Colour(0xEA6D4A),
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

    @commands.command(
        aliases=["clr", "color"],
        brief="Get colour information from hex value",
        description=(
            "Get colour information from hex value\n\nCan use either `0x` or "
            "`#` prefix (`0xFFFFFF` or `#FFFFFF`)"
        ),
        example=("colour ffffff", "clr 0xffffff", "color #ffffff"),
    )
    async def colour(self, ctx, value: str):
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

    @commands.command(aliases=["lvl", "rank"], hidden=True, brief="Level")
    async def level(self, ctx):
        return await ctx.try_reply(
            "https://tenor.com/view/stop-it-get-some-help-gif-7929301"
        )

    @commands.group(
        aliases=["em"],
        brief="Get an emoji's information",
        description=(
            "Get an emoji's information\n\nWill execute `emoji info` by "
            "default when there's no any subcommands used"
        ),
        example=(
            "emoji info :thonk:",
            "em ? :thinkies:",
            "emoji steal :KEKW:",
        ),
        invoke_without_command=True,
    )
    async def emoji(self, ctx, emoji: Union[discord.Emoji, discord.PartialEmoji, str]):
        await self.emojiinfo(ctx, emoji)

    @emoji.command(
        name="info",
        aliases=["?"],
        brief="Get an emoji's information",
        description="Get an emoji's information\n\nSupports Unicode/built-in emojis",
        example=(
            "emoji info :pog:",
            "em info :KEKW:",
            "em ? 🤔",
        ),
    )
    async def emojiinfo(
        self, ctx, emoji: Union[discord.Emoji, discord.PartialEmoji, str]
    ):
        try:
            e = ZEmbed.default(
                ctx,
                title=f":{emoji.name}:",
                description=f"`ID: {emoji.id}`\n`Type: Custom Emoji`",
            )
            e.set_image(url=emoji.url)
        except AttributeError:
            try:
                e = ZEmbed.default(
                    ctx,
                    title=" - ".join(
                        (
                            emoji,
                            hex(ord(emoji)).replace("0x", r"\u"),
                            unicodedata.name(emoji),
                        )
                    ),
                    description="`Type: Unicode`",
                )
            except TypeError:
                return await ctx.try_reply("`{}` is not a valid emoji!".format(emoji))
        return await ctx.try_reply(embed=e)

    @emoji.command(
        brief="Steal a custom emoji",
        description="Steal a custom emoji\n\nUnicode emojis are not supported!",
        example=("emoji steal :shuba:", "em steal :thonk:", "emoji steal :LULW:"),
    )
    @checks.mod_or_permissions(manage_emojis=True)
    async def steal(self, ctx, emoji: Union[discord.Emoji, discord.PartialEmoji]):
        async with self.bot.session.get(str(emoji.url)) as req:
            emojiByte = await req.read()
        try:
            addedEmoji = await ctx.guild.create_custom_emoji(
                name=emoji.name, image=emojiByte
            )
        except discord.Forbidden:
            return await ctx.try_reply("I don't have permission to `Manage Emojis`!")

        e = ZEmbed.default(
            ctx,
            title="{} `:{}:` has been added to the server".format(
                addedEmoji, addedEmoji.name
            ),
        )
        return await ctx.try_reply(embed=e)

    @steal.error
    async def stealErr(self, ctx, error):
        if isinstance(error, commands.BadUnionArgument):
            await ctx.try_reply("Unicode is not supported!")

    @commands.command(
        aliases=["jsh"],
        brief="Get japanese word",
        description="Get japanese word from english/japanese/romaji/text",
        example=(
            "joshi こんにちは",
            "jsh konbanha",
            "joshi hello",
        ),
    )
    async def jisho(self, ctx, *, words):
        async with ctx.bot.session.get(
            "https://jisho.org/api/v1/search/words", params={"keyword": words}
        ) as req:
            result = await req.json()

            try:
                result = result["data"][0]
            except:
                return await ctx.try_reply(
                    "Sorry, couldn't find any words matching `{}`".format(words)
                )

            e = ZEmbed.default(
                ctx, title=f"{result['slug']}「 {result['japanese'][0]['reading']} 」"
            )
            e.set_author(
                name="jisho.org",
                icon_url="https://assets.jisho.org/assets/touch-icon-017b99ca4bfd11363a97f66cc4c00b1667613a05e38d08d858aa5e2a35dce055.png",
                url="https://jisho.org",
            )
            for sense in result["senses"]:
                name = "; ".join(sense["parts_of_speech"]) or "-"
                if sense["info"]:
                    name += f"「 {'; '.join(sense['info'])} 」"

                e.add_field(
                    name=name,
                    value="; ".join(
                        f"`{sense}`" for sense in sense["english_definitions"]
                    ),
                    inline=False,
                )
            await ctx.try_reply(embed=e)


def setup(bot):
    bot.add_cog(Info(bot))
