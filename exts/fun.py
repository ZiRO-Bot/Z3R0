"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import asyncio
import discord


from core.mixin import CogMixin
from discord.ext import commands
from exts.api import reddit
from random import choice


class Fun(commands.Cog, CogMixin):
    """Meme and other fun commands."""

    icon = "🎉"
    cc = True

    def __init__(self, bot):
        super().__init__(bot)
        self.reddit = reddit.Reddit(self.bot.session)

    @commands.command()
    async def meme(self, ctx):
        """Get memes from subreddit r/memes."""
        # TODO: Add more meme subreddits
        memeSubreddits = ("memes", "funny")
        subreddit = await self.reddit.hot(choice(memeSubreddits))
        # Exclude videos since discord embed don't support video
        posts = [post for post in subreddit.posts if not post.isVideo]
        if ctx.channel.is_nsfw:
            submission = choice(posts)
        else:
            submission = choice([post for post in posts if not post.is18])

        e = discord.Embed(
            title=f"{subreddit} - {submission.title}",
            colour=discord.Colour(0xFF4500),
        )
        e.set_author(
            name="Reddit",
            icon_url="https://www.redditstatic.com/desktop2x/"
            + "img/favicon/android-icon-192x192.png",
        )
        e.add_field(name="Score", value=submission.score)
        e.add_field(name="Comments", value=submission.commentCount)

        if submission.url:
            e.set_image(url=submission.url)

        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(Fun(bot))
