import datetime as dt

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


class AnimeSearchPageSource(menus.ListPageSource):
    def __init__(self, ctx, anime):
        self.ctx = ctx

        super().__init__(anime, per_page=1)

    async def format_page(self, menu: menus.MenuPages, anime):
        isAdult = anime["isAdult"]

        desc = anime["description"]
        if desc:
            for d in ("</i>", "<i>", "<br>", "</br>"):
                desc = desc.replace(d, "")
        else:
            desc = "No description."

        maxLen = 250
        if len(desc) > maxLen:
            origLen = len(desc)
            desc = desc[:maxLen]
            hidden = "... **+{}** hidden\n(click {} to read more)".format(
                origLen - len(desc), Emojis.info
            )
            desc += hidden

        e = ZEmbed.default(
            self.ctx,
            title=anime["title"]["romaji"],
            description=desc,
        )

        rating = anime["averageScore"] or -1
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

        chNsfw = self.ctx.channel.is_nsfw()
        cover = anime["coverImage"]["large"]
        banner = anime["bannerImage"]
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
            value=", ".join([studio["name"] for studio in anime["studios"]["nodes"]])
            or "Unknown",
            inline=False,
        )

        e.add_field(name="Format", value=anime["format"].replace("_", " "))

        if str(anime["format"]).lower() in ["movie", "music"]:
            if anime["duration"]:
                duration = humanize.precisedelta(
                    dt.timedelta(seconds=anime["duration"] * 60)
                )
            else:
                duration = "?"
            e.add_field(name="Duration", value=duration)
        else:
            e.add_field(name="Episodes", value=anime["episodes"] or "0")

        e.add_field(name="Status", value=str(anime["status"]).title())

        e.add_field(
            name="Genres", value=", ".join(anime["genres"]) or "Unknown", inline=False
        )

        sites = [
            "[{0['site']}]({0['url']})".format(site)
            for site in anime["externalLinks"]
            if site in STREAM_SITES
        ]
        if sites:
            e.add_field(name="Streaming Sites", value=", ".join(sites), inline=False)

        return e

    def sendSynopsis(self, anime):
        return anime["description"] or "No description."
