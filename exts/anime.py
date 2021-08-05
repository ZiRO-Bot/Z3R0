"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from discord.ext import commands

from core.mixin import CogMixin


class Anime(commands.Cog, CogMixin):
    """Cog about Anime and Manga."""

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
    async def animeSearch(self, ctx, *, name: str):
        pass


def setup(bot):
    bot.add_cog(Anime(bot))
