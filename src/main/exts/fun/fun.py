"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import io
from random import choice, randint, random, shuffle
from typing import get_args

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.app_commands import locale_str as _
from discord.ext import commands

from ...core import checks
from ...core import commands as cmds
from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.errors import ArgumentError
from ...core.mixin import CogMixin
from ...utils.api import reddit
from ...utils.piglin import Piglin
from ._flags import FINDSEED_MODES, FindseedFlags


class Fun(commands.Cog, CogMixin):
    """Meme and other fun commands."""

    icon = "🎉"
    cc = True

    def __init__(self, bot):
        super().__init__(bot)
        self.reddit = reddit.Reddit(self.bot.session)

    @cmds.command(
        name=_("meme"),
        hybrid=True,
        description=_("meme-desc"),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def meme(self, ctx):
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
            icon_url="https://www.redditstatic.com/desktop2x/" + "img/favicon/android-icon-192x192.png",
        )
        e.add_field(name="Score", value=submission.score)
        e.add_field(name="Comments", value=submission.commentCount)

        if submission.url:
            e.set_image(url=submission.url)

        await msg.edit(embed=e)

    @app_commands.choices(args=[Choice(name=i, value=i) for i in get_args(FINDSEED_MODES)])
    @app_commands.rename(args="mode")
    @cmds.command(
        name=_("findseed"),
        description=_("findseed-desc"),
        aliases=("fs", "vfs"),
        hybrid=True,
        usage="[options]",
        extras=dict(
            example=("findseed", "findseed mode: classic", "fs mode: pipega"),
            flags={"mode": "Change display mode (modes: visual, classic, pipega or pepiga, halloween)"},
        ),
    )
    @commands.cooldown(5, 25, commands.BucketType.user)
    async def findseed(self, ctx, *, args: FindseedFlags = None):
        availableMode = get_args(FINDSEED_MODES)
        aliasesMode = {"pepiga": "pipega"}

        try:
            argMode = aliasesMode.get(args.mode, args.mode)  # type: ignore
        except AttributeError:
            argMode = None

        mode = "visual" if argMode not in availableMode else argMode

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
            halloween={
                "{frame}": "<:pumpkinUnlit:894570332227268638>",
                "{eye}": "<:pumpkinLit:894570365148352592>",
            },
        )

        eyes = ["{eye}" if randint(1, 10) == 1 else "{frame}" for _ in range(12)]
        eyeCount = sum([1 for i in eyes if i == "{eye}"])

        # people with rigged amount of eyes
        rig = {
            518154918276628490: 12,
            575014590371463178: 12,
            755667043117695036: 12,
        }
        executorId = ctx.author.id
        if executorId in rig:
            rig = rig[executorId]
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
            return await ctx.try_reply(
                "<@{}> -> your seed is a {} eye{}".format(
                    executorId,
                    eyeCount,
                    "s" if eyeCount > 1 or eyeCount == 0 else "",
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

        portalFrame = "\u200b"
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

    @commands.command(
        description="Ping random member",
        help='\nAlso known as "Discord\'s mistake"\n **Note**: Only available on April Fools (UTC)!',
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @checks.isAprilFool()
    async def someone(self, ctx: Context):
        allowPingGuilds = (793642143243173888,)
        allowedMentions = discord.AllowedMentions.none()
        if ctx.requireGuild().id in allowPingGuilds:
            allowedMentions = discord.AllowedMentions(users=True)
        await ctx.send(choice(ctx.requireGuild().members).mention, allowed_mentions=allowedMentions)

    @cmds.command(
        name=_("httpcat"),
        usage="(status code)",
        description=_("httpcat-desc"),
        hybrid=True,
        extras=dict(example=("httpcat 404",)),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def httpcat(self, ctx: Context, status_code: int):
        async with ctx.session.get(url=f"https://http.cat/{status_code}") as res:
            image = io.BytesIO(await res.read())
            img = discord.File(fp=image, filename="httpcat.jpg")
            await ctx.try_reply(file=img)

    @cmds.command(
        name=_("pp"),
        description=_("pp-desc"),
        hybrid=True,
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pp(self, ctx):
        pp = "8" + "=" * randint(1, 500) + "D"
        e = ZEmbed.default(
            ctx,
            title="Your pp looks like this:",
            description="`{}`".format(pp),
            colour=discord.Colour.random(),
        )
        await ctx.send(embed=e)

    @cmds.command(
        name=_("isimpostor"),
        aliases=("isimposter",),
        description=_("isimpostor-desc"),
        hybrid=True,
        usage="[impostor count] [player count]",
    )
    @commands.cooldown(3, 25, commands.BucketType.user)
    async def isimpostor(self, ctx, impostor: commands.Range[int, 1, 3] = 1, player: commands.Range[int, 4, 15] = 10):
        if impostor < 1:
            impostor = 1
            await ctx.send("Impostor count has been set to `1`")
        if impostor > player:
            impostor = player

        if random() < impostor / player:
            await ctx.send(f"{ctx.author.mention}, you're an impostor!")
        else:
            await ctx.send(f"{ctx.author.mention}, you're a crewmate!")

    @cmds.command(
        name=_("dadjokes"),
        aliases=("badjokes",),
        description=_("dadjokes-desc"),
        hybrid=True,
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def dadjokes(self, ctx):
        headers = {"accept": "application/json"}
        async with self.bot.session.get("https://icanhazdadjoke.com/", headers=headers) as req:
            dadjoke = (await req.json())["joke"]
        e = ZEmbed.default(ctx, title=dadjoke, color=discord.Colour(0xFEDE58))
        e.set_author(
            name="icanhazdadjoke",
            icon_url="https://raw.githubusercontent.com/null2264/null2264/master/epicface.png",
        )
        await ctx.send(embed=e)

    @cmds.command(
        name=_("rps"),
        usage="(choice)",
        description=_("rps-desc"),
        hybrid=True,
        extras=dict(
            example=("rps rock",),
        ),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rps(self, ctx, choice_: str):
        choice_ = choice_.lower()
        rps = ("rock", "paper", "scissors")
        botChoice = choice(rps)

        if botChoice == choice_:
            result = "It's a Tie!"

        elif botChoice == rps[0]:

            def f(x):  # type: ignore
                return {"paper": "Paper wins!", "scissors": "Rock wins!"}.get(x, "Rock wins!")

            result = f(choice_)

        elif botChoice == rps[1]:

            def f(x):  # type: ignore
                return {"rock": "Paper wins!", "scissors": "Scissors wins!"}.get(x, "Paper wins!")

            result = f(choice_)

        elif botChoice == rps[2]:

            def f(x):
                return {"paper": "Scissors wins!", "rock": "Rock wins!"}.get(x, "Scissors wins!")

            result = f(choice_)

        else:
            return

        if choice_ == "noob":
            result = "Noob wins!"

        await ctx.try_reply(
            f"You chose ***{choice_.capitalize()}***." + f" I chose ***{botChoice.capitalize()}***.\n{result}"
        )

    @rps.autocomplete("choice_")
    async def choiceSuggestion(self, inter, choice):
        rps = ("rock", "paper", "scissors")
        return [app_commands.Choice(name=i, value=i) for i in rps]

    @commands.command(aliases=("find-waifu",), description="Just Rafael and his waifu")
    @checks.isRafael()
    async def findwaifu(self, ctx):
        f = discord.File("./assets/img/rafaelAndHisWaifu.png", filename="img.png")
        return await ctx.try_reply(file=f)

    @cmds.command(
        name=_("flip"),
        description=_("flip-desc"),
        hybrid=True,
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def flip(self, ctx):
        await ctx.try_reply(f"You got {choice(['heads', 'tails'])}!")

    # TODO: Slash
    @commands.command(
        description="Simple dice roller",
        help=("\nNumber of dices are capped at 5!\n" "**Support optional size**: d4, d8, d10, d00, d12, d20"),
        usage="[dice size] (number of dice)",
        extras=dict(example=("roll 5", "roll d20", "roll d00 4")),
    )
    @commands.cooldown(1, 5, type=commands.BucketType.user)
    async def roll(self, ctx, *args):
        diceSize = {
            "d4": 4,
            "d6": 6,
            "d8": 8,
            "d10": 10,
            "d00": 100,
            "d12": 12,
            "d20": 20,
        }
        # Default size and number of dice
        selSize = 6

        try:
            selSize = diceSize[args[0]]
            diceNum = int(args[1])
        except KeyError:
            if not str(args[0]).isdigit():
                raise ArgumentError("Invalid arguments") from None
            diceNum = int(args[0])
        except (IndexError, ValueError):
            diceNum = 1

        # Cap dice number up to 5 to prevent bot from freezing
        diceNum = 5 if diceNum > 5 else diceNum
        results = [
            str(randint(0 if selSize == 100 else 1, selSize)) + ("%" if selSize == 100 else "") for _ in range(diceNum)
        ]
        return await ctx.try_reply("You rolled {}".format(", ".join(results)))

    @cmds.command(
        name=_("clap"),
        aliases=("👏",),
        description="👏",
        hybrid=True,
        extras=dict(example=("clap hell yea", "clap clap clap")),
    )
    @commands.cooldown(1, 5, type=commands.BucketType.user)
    async def clap(self, ctx, *, text: str = ""):
        return await ctx.try_reply(text.replace(" ", " 👏 ") or " 👏 ")

    @cmds.command(
        name=_("barter"),
        description=_("barter-desc"),
        help="\n**Note**: The loot table is based on JE 1.16.1 (before nerf)",
        aliases=("piglin",),
        hybrid=True,
        usage="[amount of gold]",
        extras=dict(
            example=("barter 64", "piglin", "barter 262"),
        ),
    )
    @commands.cooldown(5, 25, type=commands.BucketType.user)
    async def barter(self, ctx, gold: commands.Range[int, 1, 2240] = 64):
        # limit gold amount up to 2240 (Minecraft inventory limit)
        if gold > 2240:
            gold = 2240
        if gold <= 0:
            gold = 1

        trade = Piglin(gold)

        items = {}
        for item in trade.items:
            try:
                items[item.name][1] += item.quantity
            except KeyError:
                items[item.name] = [item.id, item.quantity]

        def emoji(name: str):
            return {
                "enchanted-book": "<:enchantedbook:807261766065192971>",
                "iron-boots": "<:ironboots:807261701363597322>",
                "iron-nugget": "<:ironnugget:807261807601385473>",
                "splash-potion-fire-res": "<:splashpotionfireres:807261948017377300>",
                "potion-fire-res": "<:potionfireres:807262044478504967>",
                "quartz": "<:quartz:807262092032999484>",
                "glowstone-dust": "<:glowstonedust:807262151826735105>",
                "magma-cream": "<:magmacream:807262199684005918>",
                "ender-pearl": "<:enderpearl:807261299817709608>",
                "string": "<:string:807262264381014086>",
                "fire-charge": "<:firecharge:807262322522718219>",
                "gravel": "<:gravel3D:807535983448948766>",
                "leather": "<:leather:807262494619860993>",
                "nether-brick": "<:netherbricks3D:807536302365999114>",
                "obsidian": "<:obsidian3D:807536509837770762>",
                "cry-obsidian": "<:cryobsidian3D:807536510152474644>",
                "soul-sand": "<:soulsand3D:807536744253227049>",
            }.get(name, "<:missingtexture:807536928361545729>")

        e = ZEmbed(
            ctx,
            title="Bartering with {} gold{}".format(gold, "s" if gold > 1 else ""),
            description="You got:\n\n{}".format("\n".join(["{} → {}".format(emoji(v[0]), v[1]) for v in items.values()])),
            colour=discord.Colour.gold(),
        )
        await ctx.try_reply(embed=e)
