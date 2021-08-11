"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from random import randrange

import discord
from discord.ext import commands

from core.embed import ZEmbed
from core.enums import Emojis
from core.menus import ZMenuPagesView
from core.mixin import CogMixin
from utils.api import graphql

from ._flags import AnimeSearchFlags
from ._pages import AnimeSearchPageSource
from ._query import searchQuery


class ReadMore(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction):
        view: ZMenuPagesView = self.view
        page = await view._source.get_page(view.currentPage)  # type: ignore
        synopsis = view._source.sendSynopsis(page)  # type: ignore
        e = ZEmbed(description=synopsis)
        await interaction.response.send_message(embed=e, ephemeral=True)


class AniList(commands.Cog, CogMixin):
    """Cog about Anime and Manga."""

    icon = "<:AniList:872771143797440533>"

    def __init__(self, bot):
        super().__init__(bot)
        self.anilist = graphql.GraphQL(
            "https://graphql.anilist.co", session=self.bot.session
        )

    async def anilistSearch(self, ctx, name: str, parsed, type: str = "ANIME"):
        """Function for 'manga search' and 'anime search' command"""
        type = type.upper().replace(" ", "_")

        if not name:
            return await ctx.error("You need to specify the name!")

        kwargs = {
            "name": name,
            "page": 1,
            "perPage": 25,
            "type": "ANIME",
        }
        if parsed.format_:
            kwargs["format"] = parsed.format_.strip().upper().replace(" ", "_")

        req = await self.anilist.queryPost(
            searchQuery,
            **kwargs,
        )
        aniData = req["data"]["Page"]["media"]
        if not aniData:
            return await ctx.error(
                f"No {type.lower().replace('_', '')} called `{name}` found.",
                title="No result",
            )

        menu = ZMenuPagesView(ctx, source=AnimeSearchPageSource(aniData))
        menu.add_item(ReadMore(emoji=Emojis.info))
        await menu.start()

    async def anilistRandom(self, ctx, type: str = "ANIME"):
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

        e = ZEmbed.default(
            ctx, title=mediaData["title"]["userPreferred"], url=mediaData["siteUrl"]
        ).set_image(url=f"https://img.anili.st/media/{id}")

        await ctx.try_reply(embed=e)

    @commands.group(
        aliases=("ani",),
        brief="Get anime's information",
    )
    async def anime(self, ctx):
        pass

    @anime.command(
        name="search",
        aliases=("s", "find", "?", "info"),
        brief="Search for an anime with AniList",
        usage="(name) [options]",
        extras=dict(
            flags={
                "format": (
                    "Anime's format (TV, TV SHORT, OVA, ONA, MOVIE, " "SPECIAL, MUSIC)"
                ),
            }
        ),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def animeSearch(self, ctx, *, arguments: AnimeSearchFlags):
        name, parsed = arguments

        await self.anilistSearch(ctx, name, parsed, "ANIME")

    @anime.command(name="random", brief="Get random anime")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def animeRandom(self, ctx):
        await self.anilistRandom(ctx)

    @commands.group(brief="Get manga's information")
    async def manga(self, ctx):
        pass

    @manga.command(
        name="search",
        aliases=("s", "find", "?", "info"),
        brief="Search for a manga with AniList",
        usage="(name) [options]",
        extras=dict(
            flags={
                "format": "Manga's format (MANGA, NOVEL, ONE SHOT)",
            }
        ),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mangaSearch(self, ctx, *, arguments: AnimeSearchFlags):
        name, parsed = arguments

        await self.anilistSearch(ctx, name, parsed, "MANGA")

    @manga.command(name="random", brief="Get random manga")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mangaRandom(self, ctx):
        await self.anilistRandom(ctx, type="MANGA")
