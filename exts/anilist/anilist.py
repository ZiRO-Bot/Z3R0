"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from random import randrange

from discord.ext import commands

from core.embed import ZEmbed
from core.menus import ZMenuPagesView
from core.mixin import CogMixin
from utils.api import graphql
from utils.format import separateStringFlags

from ._flags import AnimeSearchFlags
from ._pages import AnimeSearchPageSource


class AniList(commands.Cog, CogMixin):
    """Cog about Anime and Manga."""

    icon = "<:AniList:872771143797440533>"

    def __init__(self, bot):
        super().__init__(bot)
        self.anilist = graphql.GraphQL(
            "https://graphql.anilist.co", session=self.bot.session
        )

    @commands.group(
        brief="Get information about anime",
    )
    async def anime(self, ctx):
        pass

    @anime.command(
        name="search",
        aliases=("find", "?", "info"),
        brief="Search for an anime with AniList",
    )
    async def animeSearch(self, ctx, *, arguments: str):
        name, args = separateStringFlags(arguments)
        if not name:
            await ctx.error("You need to specify the name!")
        parsed = await AnimeSearchFlags.convert(ctx, args)

        query = await self.anilist.queryPost(
            """
            query($name: String, $format: MediaFormat, $page: Int, $perPage: Int=5) {
                Page(perPage:$perPage, page:$page) {
                    pageInfo{hasNextPage, currentPage, lastPage}
                    media(search:$name,type:ANIME,format:$format){
                        id,
                        format,
                        title {
                            romaji,
                            english
                        },
                        episodes,
                        duration,
                        status,
                        startDate {
                            year,
                            month,
                            day
                        },
                        endDate {
                            year,
                            month,
                            day
                        },
                        genres,
                        coverImage {
                            large
                        },
                        bannerImage,
                        description,
                        averageScore,
                        studios { nodes { name } },
                        seasonYear,
                        externalLinks {
                            site,
                            url
                        },
                        isAdult
                    }
                }
            }
            """,
            name=name,
            format=parsed.format_.strip().upper().replace(" ", "_"),
            page=1,
            perPage=10,
        )
        aniData = query["data"]["Page"]["media"]
        menu = ZMenuPagesView(
            ctx, source=AnimeSearchPageSource(ctx, aniData), timeout=3
        )
        await menu.start()

    @commands.command(brief="Get random anime")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def findanime(self, ctx):
        query = await self.anilist.queryPost(
            """
            {
                Page(perPage:1) {
                    pageInfo {
                        lastPage
                    }
                    media(type: ANIME, format_in:[MOVIE, TV, TV_SHORT]) {
                        id
                    }
                }
            }
            """
        )
        lastPage = query["data"]["Page"]["pageInfo"]["lastPage"]
        query = await self.anilist.queryPost(
            """
            query ($random: Int) {
                Page(page: $random, perPage: 1) {
                    pageInfo {
                        total
                    }
                    media(type: ANIME, isAdult: false, status_not: NOT_YET_RELEASED) {
                        id,
                        title { userPreferred },
                        siteUrl
                    }
                }
            }
            """,
            random=randrange(1, lastPage),
        )
        mediaData = query["data"]["Page"]["media"][0]
        id = mediaData["id"]
        e = ZEmbed.default(
            ctx, title=mediaData["title"]["userPreferred"], url=mediaData["siteUrl"]
        ).set_image(url=f"https://img.anili.st/media/{id}")
        await ctx.try_reply(embed=e)
