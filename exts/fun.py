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
from exts.utils.format import ZEmbed
from exts.utils.other import ArgumentParser
from random import choice, randint, shuffle


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

        redditColour = discord.Colour(0xFF4500)

        msg = await ctx.try_reply(embed=ZEmbed.loading(color=redditColour))

        subreddit = await self.reddit.hot(choice(memeSubreddits))

        # Exclude videos since discord embed don't support video
        posts = [post for post in subreddit.posts if not post.isVideo]
        if ctx.channel.is_nsfw:
            submission = choice(posts)
        else:
            submission = choice([post for post in posts if not post.is18])

        e = ZEmbed.default(
            ctx,
            title=f"{subreddit} - {submission.title}",
            color=redditColour,
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

        await msg.edit(embed=e)

    @commands.command(
        brief="Get your minecraft seed's eye count",
        aliases=("fs",),
        extras=dict(
            example=("findseed", "findseed mode: classic", "fs mode: pipega"),
            flags={"mode": "Change display mode (modes: visual, classic, pipega)"},
        ),
    )
    @commands.cooldown(1, 25, commands.BucketType.guild)
    async def findseed(self, ctx, *, arguments: str = None):
        availableMode = ("visual", "classic", "pipega")
        mode = "visual"

        if arguments is not None:
            parser = ArgumentParser(allow_abbrev=False)
            parser.add_argument("--mode")

            parsed, _ = await parser.parse_known_from_string(arguments)

            if parsed.mode:
                mode = str(parsed.mode).lower()
                mode = "visual" if mode not in availableMode else mode

        defaultEmojis = {
            "{air}": "<:empty:754550188269633556>",
            "{frame}": "<:portal:754550231017979995>",
            "{eye}": "<:eye:754550267382333441>",
            "{end_portal}": "<:endPortal:800191496598978560>",
            "{lava}": "<a:lavaAnimated:800215203614031892>",
        }

        emojis = dict(
            visual=defaultEmojis,
            pipega={
                "{frame}": "<:piog:866175218540085248>",
                "{eye}": "<:pipega:866175257982140456>",
                "{lava}": "<:empty:754550188269633556>",
                "{end_portal}": "<:empty:754550188269633556>",
            },
        )

        eyes = ["{eye}" if randint(1, 10) == 1 else "{frame}" for i in range(12)]
        eyeCount = sum([1 for i in eyes if i == "{eye}"])

        # rig stuff
        rig = {518154918276628490: 12}
        if ctx.author.id in rig:
            rig = rig[ctx.author.id]
            eyeCount = rig
            if mode != "classic":
                # cap rig (can't go below 0 or above 12)
                if rig < 0:
                    rig = 0
                elif rig > 12:
                    rig = 12
                eyes = (["{eye}"] * rig) + (["{frame}"] * (12 - rig))
                if 0 < rig < 12:
                    # scramble the eyes position
                    shuffle(eyes)

        if mode == "classic":
            return await ctx.send(
                "{} -> your seed is a {} eye{}".format(
                    ctx.author.mention,
                    eyeCount,
                    "s" if eyeCount == 0 or eyeCount > 1 else "",
                )
            )

        # "render" portal
        selEye = 0
        # Selected emojis
        selEmojis = emojis[mode]
        frame = selEmojis.get("{frame}", defaultEmojis["{frame}"])
        eye = selEmojis.get("{eye}", defaultEmojis["{eye}"])
        lava = selEmojis.get("{lava}", defaultEmojis["{lava}"])
        end_portal = selEmojis.get("{end_portal}", defaultEmojis["{end_portal}"])
        air = selEmojis.get("{air}", defaultEmojis["{air}"])

        portalFrame = ""
        for row in range(5):
            for col in range(5):
                if ((col == 0 or col == 4) and (row != 0 and row != 4)) or (
                    (row == 0 or row == 4) and (col > 0 and col < 4)
                ):
                    selEye += 1
                    portalFrame += eye if eyes[selEye - 1] == "{eye}" else frame
                elif (col != 0 or col != 4) and (col > 0 and col < 4):
                    portalFrame += end_portal if eyeCount >= 12 else lava
                else:
                    portalFrame += air
            portalFrame += "\n"

        e = ZEmbed.default(
            ctx,
            title=f"findseed - Your seed is a **{eyeCount}** eye",
            description=portalFrame,
            color=discord.Colour(0x38665E),
        )
        await ctx.try_reply(embed=e)

    # @commands.command(brief="Ping random member")
    # async def someone(self, ctx):
    #     await ctx.send(choice(ctx.guild.members).mention)


def setup(bot):
    bot.add_cog(Fun(bot))
