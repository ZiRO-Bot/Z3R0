from discord.ext import menus

from core.embed import ZEmbed
from core.enums import Emojis


class AnimeSearchPageSource(menus.ListPageSource):
    def __init__(self, ctx, anime):
        self.ctx = ctx

        super().__init__(anime, per_page=1)

    async def format_page(self, menu: menus.MenuPages, anime):
        isAdult = anime["isAdult"]

        # print(anime)
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

        return e

    def sendSynopsis(self, anime):
        return anime["description"] or "No description."
