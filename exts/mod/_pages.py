from discord.ext import menus

from core.embed import ZEmbed
from core.menus import ZMenuView
from utils.format import formatDiscordDT


class CaseListSource(menus.ListPageSource):
    def __init__(self, moderator, cases) -> None:
        self.moderator = moderator
        self.totalCases = len(cases)
        super().__init__(cases, per_page=5)

    async def format_page(self, menu: ZMenuView, cases):
        moderator = self.moderator

        e = ZEmbed(title=f"{moderator.display_name}'s cases")
        e.set_author(name=moderator, icon_url=moderator.display_avatar.url)

        for case in cases:
            timestamp = case[4]
            formattedTime = "`Unknown`"
            if timestamp:
                formattedTime = formatDiscordDT(timestamp, "R")

            e.add_field(
                name=f"#{case[0]}: **`{case[1]}`** [{formattedTime}]",
                value=case[3],
                inline=False,
            )

        e.set_footer(text=f"{self.totalCases} cases in total")
        return e
