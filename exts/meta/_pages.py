from discord.ext import menus

from core.embed import ZEmbed
from utils.format import cleanifyPrefix


class PrefixesPageSource(menus.ListPageSource):
    def __init__(self, ctx, prefixes):
        self.prefixes = prefixes
        self.ctx = ctx

        super().__init__(prefixes, per_page=6)

    async def format_page(self, menu: menus.MenuPages, prefixes: list):
        ctx = self.ctx

        e = ZEmbed(
            title="{} Prefixes".format(ctx.guild), description="**Custom Prefixes**:\n"
        )

        if menu.current_page == 0:
            prefixes.pop(0)
            prefixes.pop(0)
            e.description = (
                "**Default Prefixes**: `{}` or `{} `\n\n**Custom Prefixes**:\n".format(
                    ctx.bot.defPrefix, cleanifyPrefix(ctx.bot, ctx.me.mention)
                )
            )
        e.description += (
            "\n".join([f"• `{cleanifyPrefix(ctx.bot, p)}`" for p in prefixes])
            or "No custom prefix."
        )
        return e
