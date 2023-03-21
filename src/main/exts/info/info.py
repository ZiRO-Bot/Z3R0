"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import datetime as dt
import unicodedata
from contextlib import suppress
from typing import Union

import discord
from aiohttp import InvalidURL, client_exceptions
from discord.app_commands import locale_str as _
from discord.ext import commands

from ...core import checks
from ...core import commands as cmds
from ...core.context import Context
from ...core.converter import MemberOrUser
from ...core.embed import ZEmbed
from ...core.mixin import CogMixin
from ...utils import pillow
from ...utils.api.openweather import CityNotFound, OpenWeatherAPI
from ...utils.format import formatDiscordDT, renderBar
from ...utils.other import authorOrReferenced, utcnow


class Info(commands.Cog, CogMixin):
    """Commands that gives you information."""

    icon = "<:info:783206485051441192>"
    cc = True

    def __init__(self, bot):
        super().__init__(bot)
        self.openweather = OpenWeatherAPI(key=bot.config.openWeatherToken, session=self.bot.session)

    # TODO: Slash
    @commands.command(aliases=("av", "userpfp", "pfp"), description="Get member's avatar image")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def avatar(self, ctx: Context, user: MemberOrUser = None):
        user = user or await authorOrReferenced(ctx)  # type: ignore

        avatar: discord.Asset = user.display_avatar  # type: ignore

        # Links to avatar (with different formats)
        links = (
            "[`JPEG`]({})"
            " | [`PNG`]({})"
            " | [`WEBP`]({})".format(
                avatar.with_format("jpg").url,
                avatar.with_format("png").url,
                avatar.with_format("webp").url,
            )
        )
        if avatar.is_animated():
            links += " | [`GIF`]({})".format(avatar.with_format("gif").url)

        # Embed stuff
        e = ZEmbed.default(
            ctx,
            title="{}'s Avatar".format(user.name),  # type: ignore
            description=links,
        )
        e.set_image(url=avatar.with_size(1024).url)
        await ctx.try_reply(embed=e)

    @cmds.command(
        name=_("weather"),
        aliases=("w",),
        description=_("weather-desc"),
        hybrid=True,
        extras=dict(example=("weather Palembang", "w London")),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def weather(self, ctx: Context, *, city: str):
        if not self.openweather.apiKey:
            return await ctx.error(_("weather-api-error"))

        try:
            weatherData = await self.openweather.get_from_city(city)
        except CityNotFound as err:
            return await ctx.error(str(err))

        e = ZEmbed(
            ctx,
            title="{0.city}, {0.country}".format(weatherData),
            description=await ctx.translate(
                _(
                    "weather-temperature-feel",
                    tempFeels=weatherData.tempFeels.celcius,
                    detail=weatherData.weatherDetail,
                )
            ),
            colour=discord.Colour(0xEA6D4A),
        )
        e.set_author(
            name="OpenWeather",
            icon_url="https://openweathermap.org/themes/openweathermap/assets/vendor/owm/img/icons/logo_60x60.png",
        )
        e.add_field(name=await ctx.translate(_("weather-temperature")), value="{}°C".format(weatherData.temp.celcius))
        e.add_field(name=await ctx.translate(_("weather-humidity")), value=weatherData.humidity)
        e.add_field(name=await ctx.translate(_("weather-wind")), value=str(weatherData.wind))
        e.set_thumbnail(url=weatherData.iconUrl)
        await ctx.try_reply(embed=e)

    @cmds.command(
        name=_("color"),
        aliases=("clr", "colour"),
        description=_("color-desc"),
        help="\n\nCan use either `0x` or " "`#` prefix (`0xFFFFFF` or `#FFFFFF`)",
        hybrid=True,
        extras=dict(example=("colour ffffff", "clr 0xffffff", "color #ffffff")),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def colour(self, ctx: Context, value: str):
        # Pre processing
        value = value.lstrip("#")[:6]
        value = value.ljust(6, "0")

        try:
            h = str(hex(int(value, 16)))[2:]
            h = h.ljust(6, "0")
        except ValueError:
            return await ctx.error(_("color-error"))

        # Convert HEX into RGB
        RGB = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

        image = await pillow.rectangle(*RGB)  # type: ignore
        f = discord.File(fp=image, filename="rect.png")

        e = ZEmbed.default(
            ctx,
            title=await ctx.translate(_("color-title", hexValue=h)),
            colour=discord.Colour(int(h, 16) if h != "ffffff" else 0xFFFFF0),
        )
        e.set_thumbnail(url="attachment://rect.png")
        e.add_field(name=await ctx.translate(_("color-hex")), value=f"#{h}")
        e.add_field(name=await ctx.translate(_("color-rgb")), value=", ".join([str(x) for x in RGB]))
        return await ctx.try_reply(file=f, embed=e)

    @commands.command(aliases=("lvl", "rank"), hidden=True, description="Level")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def level(self, ctx):
        return await ctx.try_reply("https://tenor.com/view/stop-it-get-some-help-gif-7929301")

    # TODO: Slash
    @commands.group(
        aliases=("em", "emote"),
        description="Get an emoji's information",
        help="\n\nWill execute `emoji info` by " "default when there's no any subcommands used",
        extras=dict(
            example=(
                "emoji info :thonk:",
                "em ? :thinkies:",
                "emoji steal :KEKW:",
            )
        ),
        invoke_without_command=True,
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def emoji(self, ctx: Context, emoji: Union[discord.Emoji, discord.PartialEmoji, str]):
        # TODO: Add emoji list
        await ctx.try_invoke(self.emojiInfo, emoji)

    @emoji.command(
        name="info",
        aliases=("?",),
        description="Get an emoji's information",
        help="\n\nSupports Unicode/built-in emojis",
        extras=dict(
            example=(
                "emoji info :pog:",
                "em info :KEKW:",
                "em ? 🤔",
            )
        ),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def emojiInfo(self, ctx: Context, emoji: Union[discord.PartialEmoji, str]):
        try:
            e = ZEmbed.default(
                ctx,
                title=f":{emoji.name}:",  # type: ignore
                description=f"`ID: {emoji.id}`\n`Type: Custom Emoji`",  # type: ignore
            )
            e.set_image(url=emoji.url)  # type: ignore
        except AttributeError:
            try:
                strEm: str = str(emoji)
                digit = f"{ord(strEm):x}"
                e = ZEmbed.default(
                    ctx,
                    title=" - ".join(
                        (
                            strEm,
                            f"\\u{digit}",
                            unicodedata.name(strEm, "Name not found"),
                        )
                    ),
                    description="`Type: Unicode`",
                )
            except TypeError:
                return await ctx.error("`{}` is not a valid emoji!".format(emoji))
        return await ctx.try_reply(embed=e)

    @emoji.command(
        name="steal",
        description="Steal a custom emoji",
        help="\n\nUnicode emojis are not supported!",
        extras=dict(
            example=("emoji steal :shuba:", "em steal :thonk:", "emoji steal :LULW:"),
            perms={
                "bot": "Manage Emojis and Stickers",
                "user": "Manage Emojis and Stickers",
            },
        ),
    )
    @commands.guild_only()
    @checks.mod_or_permissions(manage_emojis=True)
    async def emojiSteal(self, ctx: Context, emoji: Union[discord.Emoji, discord.PartialEmoji]):
        emojiByte = await emoji.read()

        try:
            addedEmoji = await ctx.guild.create_custom_emoji(name=emoji.name, image=emojiByte)  # type: ignore
        except discord.Forbidden:
            return await ctx.error("I don't have permission to `Manage Emojis`!")

        e = ZEmbed.default(
            ctx,
            title="{} `:{}:` has been added to the guild".format(addedEmoji, addedEmoji.name),
        )
        return await ctx.try_reply(embed=e)

    @emoji.command(
        name="add",
        description="Add a custom emoji",
        help="\n\nUnicode emojis are not supported (yet)!",
        extras=dict(
            example=(
                "emoji add shuba https://cdn.discordapp.com/emojis/855604899743793152.gif",
                "em add thonking :thonk:",
            ),
            perms={
                "bot": "Manage Emojis and Stickers",
                "user": "Manage Emojis and Stickers",
            },
        ),
        usage="(emoji name) (emoji/image url/attachment)",
    )
    @commands.guild_only()
    @checks.mod_or_permissions(manage_emojis=True)
    async def emojiAdd(
        self,
        ctx,
        name: str,
        emoji: Union[discord.Emoji, discord.PartialEmoji, str] = None,
    ):
        if emoji is not None:
            try:
                emojiByte = await emoji.read()  # type: ignore
            except AttributeError:
                # Probably a url?
                try:
                    async with self.bot.session.get(emoji) as req:  # type: ignore
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
            addedEmoji = await ctx.guild.create_custom_emoji(
                name=name,
                image=emojiByte,  # type: ignore
            )
        except discord.Forbidden:
            return await ctx.error("I don't have permission to `Manage Emojis`!")

        e = ZEmbed.default(
            ctx,
            title="{} `:{}:` has been added to the guild".format(addedEmoji, addedEmoji.name),
        )
        return await ctx.try_reply(embed=e)

    @cmds.command(
        name=_("jisho"),
        aliases=("jsh",),
        description=_("jisho-desc"),
        help=" from english/japanese/romaji/text",
        hybrid=True,
        extras=dict(
            example=(
                "joshi こんにちは",
                "jsh konbanha",
                "joshi hello",
            )
        ),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def jisho(self, ctx: Context, *, words: str):
        async with ctx.bot.session.get("https://jisho.org/api/v1/search/words", params={"keyword": words}) as req:
            result = await req.json()

            try:
                result = result["data"][0]
            except BaseException:
                return await ctx.error(_("jisho-error", words=words))

            e = ZEmbed.default(ctx, title=f"{result['slug']}「 {result['japanese'][0]['reading']} 」")
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
                    value="; ".join(f"`{sense}`" for sense in sense["english_definitions"]),
                    inline=False,
                )
            await ctx.try_reply(embed=e)

    # TODO: Slash
    @commands.command(
        aliases=("userinfo", "ui", "whois"),
        description="Get user's information",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def user(self, ctx: Context, *, _user: MemberOrUser = None):
        user: Union[discord.User, discord.Member] = _user or await authorOrReferenced(
            ctx
        )  # type: ignore # MemberOrUser or authorOrReferenced will return user/member

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
            if x.type == discord.ActivityType.custom and x.name:
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
        if (guild := ctx.guild) and user == guild.owner:
            badges.append("<:owner:747802537402564758>")

        createdAt = user.created_at.replace(tzinfo=dt.timezone.utc)
        isUser = isinstance(user, discord.User)
        joinedAt = None
        if not isUser:
            # already checked by isUser
            joinedAt = user.joined_at.replace(tzinfo=dt.timezone.utc)  # type: ignore

        avatar = user.display_avatar

        e = ZEmbed().set_author(name=user, icon_url=avatar.url).set_thumbnail(url=avatar.url)

        e.add_field(
            name="General",
            value=(
                "**Name**: {0.name} / {0.mention}\n"
                "**ID**: `{0.id}`\n"
                "**Badges**: {1}\n"
                "**Created at**: {2} ({3})".format(
                    user,
                    " ".join(badges) or "No badges.",
                    formatDiscordDT(createdAt, "F"),
                    formatDiscordDT(createdAt, "R"),
                )
            ),
            inline=False,
        )

        e.add_field(
            name="Guild",
            value=(
                "N/A"
                if isUser or not joinedAt
                else (
                    "**Joined at**: {} ({})\n".format(formatDiscordDT(joinedAt, "F"), formatDiscordDT(joinedAt, "R"))
                    + "**Role count**: ({}/{})\n".format(len(user.roles), len(user.guild.roles))  # type: ignore
                    + "**Top role**: {}".format(user.top_role.mention)  # type: ignore
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
                    "**Status**: {}\n".format(status(user.status))  # type: ignore
                    + "**Activity**: {}".format(activity(user.activity) if user.activity else "None")  # type: ignore
                )
            ),
            inline=False,
        )

        if isUser:
            e.set_footer(text="This user is not in this guild.")

        await ctx.try_reply(embed=e)

    @cmds.command(
        name=_("serverinfo"),
        aliases=("guild", "guildinfo", "gi", "server", "si"),
        description=_("serverinfo-desc"),
        hybrid=True,
    )
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def server(self, ctx):
        guild: discord.Guild = ctx.guild
        createdAt = guild.created_at

        # Counters
        bots = 0
        humans = 0
        status = {
            "online": [0, "<:status_online:747799234828435587>"],
            "offline": [0, "<:status_offline:747799247243575469>"],
            "idle": [0, "<:status_idle:747799258316668948>"],
            "dnd": [0, "<:status_dnd:747799292592259204>"],
        }
        for m in guild.members:
            if m.bot:
                bots += 1
            else:
                humans += 1

            status[str(m.status)][0] += 1

        e = ZEmbed()

        if icon := guild.icon:
            e.set_author(name=guild, icon_url=icon.url).set_thumbnail(url=icon.url)

        e.add_field(
            name=await ctx.translate(_("serverinfo-properties-title")),
            value=await ctx.translate(
                _(
                    "serverinfo-properties",
                    guildName=guild.name,
                    guildId=str(guild.id),
                    createdAt=formatDiscordDT(createdAt, "F"),
                    createdAtRelative=formatDiscordDT(createdAt, "R"),
                    guildOwner=str(guild.owner),
                    ownerMention=guild.owner.mention,  # type: ignore
                    ownerId=str(guild.owner_id),
                )
            ),
            inline=False,
        )

        e.add_field(
            name=await ctx.translate(_("serverinfo-stats-title")),
            value=await ctx.translate(
                _(
                    "serverinfo-stats",
                    categoryCount=len(guild.categories),
                    channelCount=len(guild.channels),
                    textChannelCount=len(guild.text_channels),
                    voiceChannelCount=len(guild.voice_channels),
                    stageChannelCount=len(guild.stage_channels),
                    otherChannels="<:text_channel:747744994101690408> {} ".format(len(guild.text_channels))
                    + "<:voice_channel:747745006697185333> {} ".format(len(guild.voice_channels))
                    + "<:stagechannel:867970076475813908> {} ".format(len(guild.stage_channels)),
                    memberCount=bots + humans,
                    humanCount=humans,
                    botCount=bots,
                    memberStatus=" ".join([f"{emoji}{count}" for count, emoji in status.values()]),
                    boostCount=guild.premium_subscription_count,
                    boostLevel=guild.premium_tier,
                    roleCount=len(guild.roles),
                )
            ),
            inline=False,
        )

        e.add_field(
            name=await ctx.translate(_("serverinfo-settings-title")),
            value=await ctx.translate(
                _(
                    "serverinfo-settings",
                    verificationLevel=str(guild.verification_level),
                    mfaLevel=guild.mfa_level,
                )
            ),
            inline=False,
        )

        await ctx.try_reply(embed=e)

    @cmds.command(
        name="spotify",
        aliases=("spotifyinfo", "spot"),
        description=_("spotify-desc"),
        hybrid=True,
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def spotify(self, ctx: Context, user: discord.Member = None):
        user = user or await authorOrReferenced(ctx)  # type: ignore

        spotify: discord.Spotify = discord.utils.find(
            lambda s: isinstance(s, discord.Spotify), user.activities  # type: ignore
        )  # discord.Spotify is ActivityTypes
        if not spotify:
            return await ctx.error(_("spotify-error", user=user.mention))

        e = (
            ZEmbed(
                title=spotify.title,
                colour=spotify.colour,
                url="https://open.spotify.com/track/{}".format(spotify.track_id),
            )
            .set_author(name="Spotify", icon_url="https://i.imgur.com/PA3vvdN.png")
            .set_thumbnail(url=spotify.album_cover_url)
        )

        # duration
        cur, dur = (
            utcnow() - spotify.start.replace(tzinfo=dt.timezone.utc),
            spotify.duration,
        )

        # Bar stuff
        barLength = 5 if user.is_on_mobile() else 17
        bar = renderBar(
            int(cur.seconds / dur.seconds) * 100,
            fill="─",
            empty="─",
            point="⬤",
            length=barLength,
        )

        e.add_field(name=await ctx.translate(_("spotify-artist")), value=", ".join(spotify.artists))

        e.add_field(name=await ctx.translate(_("spotify-album")), value=spotify.album)

        e.add_field(
            name=await ctx.translate(_("spotify-duration")),
            value=(
                f"{cur.seconds//60:02}:{cur.seconds%60:02}" + f" {bar} " + f"{dur.seconds//60:02}:" + f"{dur.seconds%60:02}"
            ),
            inline=False,
        )
        await ctx.try_reply(embed=e)

    # TODO: Slash
    @commands.command(
        aliases=("perms",),
        description="Show what permissions a member/role has",
        usage="[member / role]",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def permissions(
        self,
        ctx: Context,
        memberOrRole: Union[discord.Member, discord.User, discord.Role, str] = None,
    ):
        if isinstance(memberOrRole, str) or memberOrRole is None:
            memberOrRole = ctx.author

        try:
            permissions = memberOrRole.permissions  # type: ignore
        except AttributeError:
            permissions = ctx.channel.permissions_for(memberOrRole)  # type: ignore

        e = ZEmbed.default(
            ctx,
            title="{}'s Permissions".format(memberOrRole.name),  # type: ignore
            description=", ".join(["`{}`".format(str(i[0]).replace("_", " ").title()) for i in permissions if i[1] is True]),
        )
        with suppress(AttributeError):
            e.set_thumbnail(url=memberOrRole.display_avatar.url)  # type: ignore

        await ctx.try_reply(embed=e)

    @cmds.command(
        description=_("pypi-desc"),
        hybrid=True,
        usage="(project name)",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pypi(self, ctx: Context, project: str):
        async with self.bot.session.get(f"https://pypi.org/pypi/{project}/json") as res:
            try:
                res = await res.json()
            except client_exceptions.ContentTypeError:
                e = discord.Embed(
                    title=await ctx.translate(_("pypi-error-title")),
                    description=await ctx.translate(_("pypi-error")),
                    colour=discord.Colour(0x0073B7),
                )
                e.set_thumbnail(url="https://cdn-images-1.medium.com/max/1200/1%2A2FrV8q6rPdz6w2ShV6y7bw.png")
                return await ctx.try_reply(embed=e)

            info = res["info"]
            e = ZEmbed.minimal(
                title=f"{info['name']} · PyPI",
                description=info["summary"],
                colour=discord.Colour(0x0073B7),
            ).set_thumbnail(url="https://cdn-images-1.medium.com/max/1200/1%2A2FrV8q6rPdz6w2ShV6y7bw.png")
            e.add_field(
                name=await ctx.translate(_("pypi-author-title")),
                value=await ctx.translate(
                    _(
                        "pypi-author",
                        author=info["author"] or await ctx.translate(_("unknown")),
                        authorEmail=info["author_email"] or await ctx.translate(_("not-provided")),
                    )
                ),
                inline=False,
            )
            e.add_field(
                name=await ctx.translate(_("pypi-package-title")),
                value=await ctx.translate(
                    _(
                        "pypi-package",
                        version=info["version"],
                        license=info["license"] or await ctx.translate(_("not-specified")),
                        keywords=info["keywords"] or await ctx.translate(_("not-specified")),
                    )
                ),
                inline=False,
            )
            e.add_field(
                name=await ctx.translate(_("pypi-links-title")),
                value=await ctx.translate(
                    _(
                        "pypi-links",
                        homePage=info["home_page"],
                        projectUrl=info["project_url"],
                        releaseUrl=info["release_url"],
                        downloadUrl=info["download_url"],
                    )
                ),
                inline=False,
            )
            return await ctx.try_reply(embed=e)
