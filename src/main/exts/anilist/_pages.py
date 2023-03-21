"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import datetime as dt

import humanize
from discord.app_commands import locale_str as _
from discord.ext import menus

from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.enums import Emojis
from ...utils.other import Markdownify, isNsfw


STREAM_SITES = (
    "Amazon",
    "AnimeLab",
    "Crunchyroll",
    "Funimation",
    "Hidive",
    "Hulu",
    "Netflix",
    "Viz",
    "VRV",
)


HTML_PARSER = Markdownify()


class AnimeSearchPageSource(menus.ListPageSource):
    def __init__(self, dataList):
        super().__init__(dataList, per_page=1)
        self.__noDescription = "No description"

    async def format_page(self, menu: menus.MenuPages, data):
        ctx: Context = menu.context

        isAdult = data["isAdult"]

        self.__noDescription = await ctx.translate(_("no-description"))
        desc = HTML_PARSER.feed((data["description"] or self.__noDescription).replace("\n", ""))

        maxLen = 250
        if len(desc) > maxLen:
            origLen = len(desc)
            desc = desc[:maxLen]
            hidden = await ctx.translate(_("anilist-hidden-description", count=origLen - len(desc), emoji=Emojis.info))
            desc += hidden

        e = ZEmbed.default(
            ctx,
            title=data["title"]["romaji"],
            url=data["siteUrl"],
            description=desc,
        )

        rating = data["averageScore"] or -1
        if rating >= 90:
            ratingEmoji = "😃"
        elif rating >= 75:
            ratingEmoji = "🙂"
        elif rating >= 50:
            ratingEmoji = "😐"
        elif rating >= 0:
            ratingEmoji = "😦"
        else:
            ratingEmoji = "🤔"

        e.set_author(
            name=f"AniList | {rating}% {ratingEmoji}",
            icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
        )

        chNsfw = isNsfw(ctx.channel)
        cover = data["coverImage"]["large"]
        banner = data["bannerImage"]
        if not isAdult or (isAdult and chNsfw):
            if cover:
                e.set_thumbnail(url=cover)

            if banner:
                e.set_image(url=banner)
        elif isAdult and not chNsfw:
            if cover:
                e.set_thumbnail(url=f"https://imagemanip.null2264.repl.co/blur?url={cover}&fixed=false")

            if banner:
                e.set_image(url=f"https://imagemanip.null2264.repl.co/blur?url={banner}&fixed=false")

        e.add_field(
            name="Studios",
            value=", ".join([studio["name"] for studio in data["studios"]["nodes"]]) or "Unknown",
            inline=False,
        )

        e.add_field(name=await ctx.translate(_("anilist-format")), value=data["format"].replace("_", " "))

        if data["type"] == "ANIME":
            if data["format"] in ["MOVIE", "MUSIC"]:
                if data["duration"]:
                    duration = humanize.precisedelta(dt.timedelta(seconds=data["duration"] * 60))
                else:
                    duration = "?"
                e.add_field(name=await ctx.translate(_("anilist-duration")), value=duration)
            else:
                e.add_field(name=await ctx.translate(_("anilist-episodes")), value=data["episodes"] or "0")
        else:
            e.add_field(name=await ctx.translate(_("anilist-chapters")), value=data["chapters"] or "0")

        status = str(data["status"])
        e.add_field(name=await ctx.translate(_("anilist-status")), value=status.title())

        startDate = data["startDate"]
        if startDate["day"]:
            startDate = dt.date(**startDate)
            e.add_field(
                name=await ctx.translate(_("anilist-date-start")),
                value=startDate.isoformat(),
            )

        if status == "FINISHED":
            endDate = data["endDate"]
            if endDate["day"]:
                endDate = dt.date(**endDate)
                e.add_field(
                    name=await ctx.translate(_("anilist-date-end")),
                    value=endDate.isoformat(),
                )

        e.add_field(
            name=await ctx.translate(_("anilist-genres")),
            value=", ".join(data["genres"]) or await ctx.translate(_("anilist-unknown")),
            inline=False,
        )

        sites = ["[{0['site']}]({0['url']})".format(site) for site in data["externalLinks"] if site in STREAM_SITES]
        if sites:
            e.add_field(name=await ctx.translate(_("anilist-streaming-sites")), value=", ".join(sites), inline=False)

        return e

    def sendSynopsis(self, data):
        return HTML_PARSER.feed((data["description"] or self.__noDescription).replace("\n", ""))
