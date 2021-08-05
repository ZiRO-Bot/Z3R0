from discord.ext import menus

from core.embed import ZEmbed


class AnimeSearchPageSource(menus.ListPageSource):
    def __init__(self, ctx, anime):
        self.ctx = ctx

        super().__init__(anime, per_page=1)

    async def format_page(self, menu: menus.MenuPages, anime):
        isAdult = anime["isAdult"]

        print(anime)
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
            hidden = "... **+{}** hidden".format(origLen - len(desc))
            desc += hidden

        e = ZEmbed.default(
            self.ctx,
            title=anime["title"]["romaji"],
            description=desc,
        )

        if not isAdult:
            cover = anime["coverImage"]["large"]
            if cover:
                e.set_thumbnail(url=cover)

            banner = anime["bannerImage"]
            if banner:
                e.set_image(url=banner)

        return e
