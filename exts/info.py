"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import datetime as dt
import discord
import time
import unicodedata


from aiohttp import InvalidURL
from collections import OrderedDict
from core import checks
from core.mixin import CogMixin
from exts.api.openweather import OpenWeatherAPI, CityNotFound
from exts.utils import pillow
from exts.utils.format import ZEmbed, formatDiscordDT
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
        extras=dict(example=("weather Palembang", "w London")),
    )
    async def weather(self, ctx, *, city):
        if not self.openweather.apiKey:
            return await ctx.error(
                "OpenWeather's API Key is not set! Please contact the bot owner to solve this issue."
            )

        try:
            weatherData = await self.openweather.get_from_city(city)
        except CityNotFound as err:
            return await ctx.error(str(err))

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
        extras=dict(example=("colour ffffff", "clr 0xffffff", "color #ffffff")),
    )
    async def colour(self, ctx, value: str):
        # Pre processing
        value = value.lstrip("#")[:6]
        value = value.ljust(6, "0")

        try:
            h = str(hex(int(value, 16)))[2:]
            h = h.ljust(6, "0")
        except ValueError:
            return await ctx.error("Invalid colour value!")

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
        e.add_field(name="RGB", value=", ".join([str(x) for x in RGB]))
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
        extras=dict(
            example=(
                "emoji info :thonk:",
                "em ? :thinkies:",
                "emoji steal :KEKW:",
            )
        ),
        invoke_without_command=True,
    )
    async def emoji(self, ctx, emoji: Union[discord.Emoji, discord.PartialEmoji, str]):
        await ctx.try_invoke(self.emojiInfo, emoji)

    @emoji.command(
        name="info",
        aliases=["?"],
        brief="Get an emoji's information",
        description="Get an emoji's information\n\nSupports Unicode/built-in emojis",
        extras=dict(
            example=(
                "emoji info :pog:",
                "em info :KEKW:",
                "em ? 🤔",
            )
        ),
    )
    async def emojiInfo(
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
            # TODO: Doesn't work with :rock:, find a fix
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
                return await ctx.error("`{}` is not a valid emoji!".format(emoji))
        return await ctx.try_reply(embed=e)

    @emoji.command(
        name="steal",
        brief="Steal a custom emoji",
        description="Steal a custom emoji\n\nUnicode emojis are not supported!",
        extras=dict(
            example=("emoji steal :shuba:", "em steal :thonk:", "emoji steal :LULW:")
        ),
    )
    @checks.mod_or_permissions(manage_emojis=True)
    async def emojiSteal(self, ctx, emoji: Union[discord.Emoji, discord.PartialEmoji]):
        emojiByte = await emoji.url.read()

        try:
            addedEmoji = await ctx.guild.create_custom_emoji(
                name=emoji.name, image=emojiByte
            )
        except discord.Forbidden:
            return await ctx.error("I don't have permission to `Manage Emojis`!")

        e = ZEmbed.default(
            ctx,
            title="{} `:{}:` has been added to the guild".format(
                addedEmoji, addedEmoji.name
            ),
        )
        return await ctx.try_reply(embed=e)

    @emoji.command(
        name="add",
        brief="Add a custom emoji",
        description="Add a custom emoji\n\nUnicode emojis are not supported (yet)!",
        extras=dict(
            example=(
                "emoji add shuba https://cdn.discordapp.com/emojis/855604899743793152.gif",
                "em add thonking :thonk:",
            ),
        ),
        usage="(emoji name) (emoji/image url/attachment)",
    )
    @checks.mod_or_permissions(manage_emojis=True)
    async def emojiAdd(
        self,
        ctx,
        name: str,
        emoji: Union[discord.Emoji, discord.PartialEmoji, str] = None,
    ):
        if emoji is not None:
            try:
                emojiByte = await emoji.url.read()
            except AttributeError:
                # Probably a url?
                try:
                    async with self.bot.session.get(emoji) as req:
                        emojiByte = await req.read()
                except InvalidURL:
                    return await ctx.error(
                        "You can only pass custom emoji or image url",
                        title="Invalid Input!",
                    )
        else:
            if attachments := ctx.message.attachments:
                if str(attachments[0].content_type).startswith("image"):
                    emojiByte = await attachments[0].read()
            else:
                return await ctx.error(
                    "You need to pass custom emoji, image url, or image attachment!",
                    title="Missing Input!",
                )

        try:
            addedEmoji = await ctx.guild.create_custom_emoji(name=name, image=emojiByte)
        except discord.Forbidden:
            return await ctx.error("I don't have permission to `Manage Emojis`!")

        e = ZEmbed.default(
            ctx,
            title="{} `:{}:` has been added to the guild".format(
                addedEmoji, addedEmoji.name
            ),
        )
        return await ctx.try_reply(embed=e)

    @commands.command(
        aliases=["jsh"],
        brief="Get japanese word",
        description="Get japanese word from english/japanese/romaji/text",
        extras=dict(
            example=(
                "joshi こんにちは",
                "jsh konbanha",
                "joshi hello",
            )
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
                return await ctx.error(
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

    @commands.command(
        brief="Show covid information on certain country",
    )
    async def covid(self, ctx, *, country):
        # TODO: Remove later
        if country.lower() in ("united state of america", "america"):
            country = "US"
        if country.lower() in ("uk",):
            country = "United Kingdom"

        async with self.bot.session.get(
            "https://covid-api.mmediagroup.fr/v1/cases?country={}".format(country)
        ) as req:
            data = list((await req.json()).values())[0]
            try:
                e = ZEmbed.default(
                    ctx, title="{}'s COVID Report".format(data["country"])
                )
            except KeyError:
                return await ctx.error(
                    "**Note**: Country name is case-sensitive",
                    title="Invalid Country Name",
                )
            e.add_field(name="Recovered", value=f"{data['recovered']:,}")
            e.add_field(name="Deaths", value=f"{data['deaths']:,}")
            e.add_field(name="Confirmed Cases", value=f"{data['confirmed']:,}")
            await ctx.try_reply(embed=e)

    @commands.command(aliases=("ui", "whois"))
    async def userinfo(self, ctx, *, user: Union[discord.Member, discord.User] = None):
        if not user:
            user = await authorOrReferenced(ctx)

        def status(x):
            return {
                discord.Status.idle: "<:status_idle:747799258316668948>Idle",
                discord.Status.dnd: "<:status_dnd:747799292592259204>Do Not Disturb",
                discord.Status.online: "<:status_online:747799234828435587>Online",
                discord.Status.invisible: "<:status_offline:747799247243575469>Invisible",
            }.get(x, "<:status_offline:747799247243575469>Offline")

        def badge(x):
            return {
                discord.UserFlags.hypesquad_balance: "<:balance:747802468586356736>",
                discord.UserFlags.hypesquad_brilliance: "<:brilliance:747802490241810443>",
                discord.UserFlags.hypesquad_bravery: "<:bravery:747802479533490238>",
                discord.UserFlags.bug_hunter: "<:bughunter:747802510663745628>",
                # discord.UserFlags.booster: "<:booster:747802502677659668>",
                discord.UserFlags.hypesquad: "<:hypesquad:747802519085776917>",
                discord.UserFlags.partner: "<:partner:747802528594526218>",
                # discord.UserFlags.owner: "<:owner:747802537402564758>",
                discord.UserFlags.staff: "<:stafftools:747802548391379064>",
                discord.UserFlags.early_supporter: "<:earlysupport:747802555689730150>",
                # discord.UserFlags.verified: "<:verified:747802457798869084>",
                discord.UserFlags.verified_bot: "<:verified:747802457798869084>",
                discord.UserFlags.verified_bot_developer: "<:verified_bot_developer:748090768237002792>",
            }.get(x, "🚫")

        def activity(x):
            if x.type == discord.ActivityType.custom:
                detail = f": ``{x.name}``"
            elif x.name:
                detail = f" **{x.name}**"
            else:
                detail = ""

            return {
                discord.ActivityType.playing: "Playing",
                discord.ActivityType.watching: "Watching",
                discord.ActivityType.listening: "Listening to",
                discord.ActivityType.streaming: "Streaming",
                discord.ActivityType.competing: "Competing in",
                discord.ActivityType.custom: "Custom",
            }.get(x.type, "") + detail

        badges = [badge(x) for x in user.public_flags.all()]
        if user == ctx.guild.owner:
            badges.append("<:owner:747802537402564758>")

        createdAt = user.created_at.replace(tzinfo=dt.timezone.utc)
        isUser = isinstance(user, discord.User)
        joinedAt = None
        if not isUser:
            joinedAt = user.joined_at.replace(tzinfo=dt.timezone.utc)

        e = ZEmbed()

        e.set_author(name=user, icon_url=user.avatar_url)

        e.add_field(
            name="General",
            value=(
                "**Name**: {0.name} / {0.mention}\n".format(user)
                + "**ID**: `{}`\n".format(user.id)
                + "**Badges**: {}\n".format(" ".join(badges) or "No badges.")
                + "**Created at**: {} ({})".format(
                    formatDiscordDT(createdAt, "F"), formatDiscordDT(createdAt, "R")
                )
            ),
        )

        e.add_field(
            name="Guild",
            value=(
                "N/A"
                if isUser
                else (
                    "**Joined at**: {} ({})\n".format(
                        formatDiscordDT(joinedAt, "F"), formatDiscordDT(joinedAt, "R")
                    )
                    + "**Role count**: ({}/{})\n".format(
                        len(user.roles), len(user.guild.roles)
                    )
                    + "**Top role**: {}".format(user.top_role.mention)
                )
            ),
            inline=False,
        )

        e.add_field(
            name="Presence",
            value=(
                "N/A"
                if isUser
                else (
                    "**Status**: {}\n".format(status(user.status))
                    + "**Activity**: {}".format(
                        activity(user.activity) if user.activity else "None"
                    )
                )
            ),
            inline=False,
        )

        if isUser:
            e.set_footer(text="This user is not in this guild.")

        await ctx.try_reply(embed=e)


def setup(bot):
    bot.add_cog(Info(bot))
