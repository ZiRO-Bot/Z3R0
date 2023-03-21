"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from random import randrange
from typing import Optional

import discord
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands

from ...core import commands as cmds
from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.enums import Emojis
from ...core.menus import ZMenuPagesView
from ...core.mixin import CogMixin
from ...utils.api.graphql import GraphQL
from ._flags import AnimeSearchFlags
from ._pages import AnimeSearchPageSource
from ._query import searchQuery


class ReadMore(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction) -> None:
        view: Optional[ZMenuPagesView] = self.view
        page = await view._source.get_page(view.currentPage)  # type: ignore
        synopsis = view._source.sendSynopsis(page)  # type: ignore
        e = ZEmbed(description=synopsis)
        await interaction.response.send_message(embed=e, ephemeral=True)


class AniList(commands.Cog, CogMixin):
    """Cog about Anime and Manga."""

    icon = "<:AniList:872771143797440533>"

    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.anilist: GraphQL = GraphQL("https://graphql.anilist.co", session=self.bot.session)

    async def anilistSearch(
        self, ctx: Context, name: str, format: str | None, type: str = "ANIME"
    ) -> Optional[discord.Message]:
        """Function for 'manga search' and 'anime search' command"""
        type = type.upper().replace(" ", "_")

        if not name:
            return await ctx.error(_("anilist-search-name-empty", type=type))

        kwargs = {
            "name": name,
            "page": 1,
            "perPage": 25,
            "type": type,
        }
        if format:
            kwargs["format"] = format.strip().upper().replace(" ", "_")

        req = await self.anilist.queryPost(
            searchQuery,
            **kwargs,
        )
        aniData = req["data"]["Page"]["media"]
        if not aniData:
            return await ctx.error(
                _("anilist-search-no-result", type=type.lower().replace('_', ''), name=name),
                title=_("anilist-search-no-result-title"),
            )

        menu = ZMenuPagesView(ctx, source=AnimeSearchPageSource(aniData))
        menu.add_item(ReadMore(emoji=Emojis.info))
        await menu.start()

    async def anilistRandom(self, ctx, type: str = "ANIME") -> None:
        query = await self.anilist.queryPost(
            """
            query ($type: MediaType) {
                Page(perPage:1) {
                    pageInfo {
                        lastPage
                    }
                    media(type: $type) {
                        id
                    }
                }
            }
            """,
            type=type,
        )
        lastPage = query["data"]["Page"]["pageInfo"]["lastPage"]

        query = await self.anilist.queryPost(
            """
            query ($random: Int, $type: MediaType) {
                Page(page: $random, perPage: 1) {
                    pageInfo {
                        total
                    }
                    media(type: $type, isAdult: false, status_not: NOT_YET_RELEASED) {
                        id,
                        title { userPreferred },
                        siteUrl
                    }
                }
            }
            """,
            random=randrange(1, lastPage),
            type=type,
        )
        mediaData = query["data"]["Page"]["media"][0]

        id = mediaData["id"]

        e = ZEmbed.default(ctx, title=mediaData["title"]["userPreferred"], url=mediaData["siteUrl"]).set_image(
            url=f"https://img.anili.st/media/{id}"
        )

        await ctx.try_reply(embed=e)

    @cmds.group(name=_("anime"), aliases=("ani",), description=_("anime-desc"), hybrid=True)
    async def anime(self, _) -> None:
        pass

    @anime.command(
        name="search",
        localeName=_("anime-search"),
        aliases=("s", "find", "?", "info"),
        description=_("anime-search-desc"),
        usage="(name) [options]",
        hybrid=True,
        extras=dict(
            flags={
                "format": ("Anime's format (TV, TV SHORT, OVA, ONA, MOVIE, " "SPECIAL, MUSIC)"),
            }
        ),
    )
    @app_commands.describe(
        name=_("anime-search-arg-name"),
        format_=_("anime-search-arg-format"),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def animeSearch(self, ctx, *, arguments: AnimeSearchFlags) -> None:
        await self.anilistSearch(ctx, arguments.name, arguments.format_, "ANIME")  # type: ignore

    @animeSearch.autocomplete("format_")
    async def animeFormatSuggestion(self, inter, current: str):
        animeFormat = ("TV", "TV Short", "OVA", "ONA", "Movie", "Special", "Music")
        return [app_commands.Choice(name=i, value=i) for i in animeFormat]

    @anime.command(name="random", localeName=_("anime-random"), description=_("anime-random-desc"))
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def animeRandom(self, ctx) -> None:
        await self.anilistRandom(ctx)

    @cmds.group(
        name=_("manga"),
        description=_("manga-desc"),
        hybrid=True,
    )
    async def manga(self, _) -> None:
        pass

    @manga.command(
        name="search",
        localeName=_("manga-search"),
        aliases=("s", "find", "?", "info"),
        description=_("manga-search-desc"),
        usage="(name) [options]",
        extras=dict(
            flags={
                "format": "Manga's format (MANGA, NOVEL, ONE SHOT)",
            }
        ),
    )
    @app_commands.describe(
        name=_("manga-search-arg-name"),
        format_=_("manga-search-arg-format"),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mangaSearch(self, ctx, *, arguments: AnimeSearchFlags) -> None:
        await self.anilistSearch(ctx, arguments.name, arguments.format_, "MANGA")  # type: ignore

    @mangaSearch.autocomplete("format_")
    async def mangaFormatSuggestion(self, inter, current: str):
        mangaFormat = ("Manga", "Novel", "One Shot")
        return [app_commands.Choice(name=i, value=i) for i in mangaFormat]

    @manga.command(
        name="random",
        localeName=_("manga-random"),
        description=_("manga-random-desc"),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mangaRandom(self, ctx) -> None:
        await self.anilistRandom(ctx, type="MANGA")
