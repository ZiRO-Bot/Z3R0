from discord.ext import menus

from core.embed import ZEmbed
from core.menus import ZMenuView
from utils.format import cleanifyPrefix


class PrefixesPageSource(menus.ListPageSource):
    def __init__(self, ctx, prefixes):
        self.prefixes = prefixes
        self.ctx = ctx

        super().__init__(prefixes, per_page=6)

    async def format_page(self, menu: ZMenuView, _prefixes: list):
        ctx = self.ctx

        e = ZEmbed(
            title="{} Prefixes".format(ctx.guild), description="**Custom Prefixes**:\n"
        )

        if menu.currentPage == 0:
            _prefixes.pop(0)
            _prefixes.pop(0)
            e.description = (
                "**Default Prefixes**: `{}` or `{} `\n\n**Custom Prefixes**:\n".format(
                    ctx.bot.defPrefix, cleanifyPrefix(ctx.bot, ctx.me.mention)
                )
            )

        prefixes = []
        for prefix in _prefixes:
            fmt = "• "
            if prefix == "`":
                fmt += "`` {} ``"
            elif prefix == "``":
                fmt += "` {} `"
            else:
                fmt += "`{}`"
            prefixes.append(fmt.format(cleanifyPrefix(ctx.bot, prefix)))
        e.description += "\n".join(prefixes) or "No custom prefix."
        return e
