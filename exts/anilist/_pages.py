import datetime as dt
import re

import humanize
from discord.ext import menus

from core.embed import ZEmbed
from core.enums import Emojis


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


HTML_REGEX = re.compile(r"<(\S+)>(?P<content>.*)</\1>")


class AnimeSearchPageSource(menus.ListPageSource):
    def __init__(self, dataList):
        super().__init__(dataList, per_page=1)

    async def format_page(self, menu: menus.MenuPages, data):
        ctx = menu.context

        isAdult = data["isAdult"]

        desc = HTML_REGEX.sub(r"\g<content>", data["description"] or "No description")

        maxLen = 250
        if len(desc) > maxLen:
            origLen = len(desc)
            desc = desc[:maxLen]
            hidden = "... **+{}** hidden\n(click {} to read more)".format(
                origLen - len(desc), Emojis.info
            )
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

        chNsfw = ctx.channel.is_nsfw()
        cover = data["coverImage"]["large"]
        banner = data["bannerImage"]
        if not isAdult or (isAdult and chNsfw):
            if cover:
                e.set_thumbnail(url=cover)

            if banner:
                e.set_image(url=banner)
        elif isAdult and not chNsfw:
            if cover:
                e.set_thumbnail(
                    url=f"https://imagemanip.null2264.repl.co/blur?url={cover}&fixed=false"
                )

            if banner:
                e.set_image(
                    url=f"https://imagemanip.null2264.repl.co/blur?url={banner}&fixed=false"
                )

        e.add_field(
            name="Studios",
            value=", ".join([studio["name"] for studio in data["studios"]["nodes"]])
            or "Unknown",
            inline=False,
        )

        e.add_field(name="Format", value=data["format"].replace("_", " "))

        if data["type"] == "ANIME":
            if data["format"] in ["MOVIE", "MUSIC"]:
                if data["duration"]:
                    duration = humanize.precisedelta(
                        dt.timedelta(seconds=data["duration"] * 60)
                    )
                else:
                    duration = "?"
                e.add_field(name="Duration", value=duration)
            else:
                e.add_field(name="Episodes", value=data["episodes"] or "0")
        else:
            e.add_field(name="Chapters", value=data["chapters"] or "0")

        status = str(data["status"])
        e.add_field(name="Status", value=status.title())

        startDate = data["startDate"]
        if startDate["day"]:
            e.add_field(
                name="Start Date",
                value="{0[day]}/{0[month]}/{0[year]}".format(startDate),
            )

        if status == "FINISHED":
            endDate = data["endDate"]
            if endDate["day"]:
                e.add_field(
                    name="End Date",
                    value="{0[day]}/{0[month]}/{0[year]}".format(endDate),
                )

        e.add_field(
            name="Genres", value=", ".join(data["genres"]) or "Unknown", inline=False
        )

        sites = [
            "[{0['site']}]({0['url']})".format(site)
            for site in data["externalLinks"]
            if site in STREAM_SITES
        ]
        if sites:
            e.add_field(name="Streaming Sites", value=", ".join(sites), inline=False)

        return e

    def sendSynopsis(self, data):
        return HTML_REGEX.sub(r"\g<content>", data["description"] or "No description.")
