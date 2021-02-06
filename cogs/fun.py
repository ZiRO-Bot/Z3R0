import asyncio
import datetime
import discord
import io
import json
import os
import re

from bs4 import BeautifulSoup
from cogs.api import reddit
from cogs.errors.fun import DiceTooBig
from cogs.utilities.embed_formatting import em_ctx_send_error, embedDefault
from cogs.utilities.barter import Piglin
from discord.ext import commands
from discord.errors import Forbidden
from random import choice, randint, random
from typing import Optional


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reddit = reddit.Reddit(self.bot.session)

    def is_reddit():
        def predicate(ctx):
            reddit_id = ctx.bot.config["reddit"]["id"]
            reddit_secret = ctx.bot.config["reddit"]["secret"]
            reddit_user_agent = ctx.bot.config["reddit"]["user_agent"]
            if reddit_id and reddit_secret and reddit_user_agent:
                return True
            return False

        return commands.check(predicate)

    async def is_redarmy(ctx):
        return ctx.guild.id in [747984453585993808, 758764126679072788]

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def flip(self, ctx):
        """Flip a coin."""
        await ctx.reply(f"You got {choice(['heads', 'tails'])}!")

    @commands.command(usage="[dice size] [number of dice]", brief="Roll the dice.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roll(self, ctx, arg1: Optional[str] = "1", arg2: Optional[int] = None):
        """Roll the dice.\n\
           **Example**\n\
           ``>roll 2``\n``>roll d12 4``"""
        dice = []
        dice_dict = {}
        if arg1.startswith("d"):
            dice_size = int(arg1.split("d")[1])
            dice_number = arg2
            if not dice_number:
                dice_number = 1
        else:
            dice_size = 6
            dice_number = int(arg1)
        if dice_number > 500:
            return await ctx.send("You can only roll up to 500 dices!")
        elif dice_number > 10:
            for i in range(dice_number):
                dice_res = int(randint(1, dice_size))
                try:
                    dice_dict[dice_res] += 1
                except KeyError:
                    dice_dict[dice_res] = 1
        else:
            for i in range(dice_number):
                dice.append(int(randint(1, dice_size)))
            dice = ", ".join(str(i) for i in dice)
        if dice_dict:
            msg = f"You just rolled:\n```"
            for key, value in dice_dict.items():
                msg += f"{key}: {value}\n"
            msg += "```"
            return await ctx.reply(msg)
        await ctx.reply(f"You just rolled {dice}!")

    @commands.command(aliases=["r", "sroll"], usage="(number of roll)")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def steveroll(self, ctx, pool):
        """Roll the dice in steve's style."""
        if ctx.guild.id in self.bot.norules:
            ctx.command.reset_cooldown(ctx)
        await ctx.reply(f"You just rolled {randint(0, int(pool))}")

    @commands.command()
    async def meme(self, ctx):
        """Get memes from subreddit r/memes."""
        self.bot.c.execute(
            "SELECT meme_ch FROM servers WHERE id=?", (str(ctx.guild.id),)
        )
        meme_channel = self.bot.get_channel(int(self.bot.c.fetchone()[0] or 0))
        if not meme_channel:
            meme_channel = ctx.channel

        if ctx.channel != meme_channel:
            return await ctx.send(f"Please do this command in {meme_channel.mention}")

        memeSubreddits = ["memes", "funny"]
        subreddit = await self.reddit.hot(choice(memeSubreddits))
        posts = subreddit.posts
        submission = choice([post for post in posts if not post.is18])

        e = embedDefault(
            ctx,
            author_pos="bottom",
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
            if not submission.isVideo:
                e.set_image(url=submission.url)
            else:
                await meme_channel.send(embed=e)
                await meme_channel.send(submission.url)
                return

        await ctx.send(embed=e)

    @commands.command(
        usage="(choice)",
        brief="Rock Paper Scissors with the bot.",
        example="{prefix}rps rock",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rps(self, ctx, choice: str):
        """Rock Paper Scissors with the bot."""
        choice = choice.lower()
        rps = ["rock", "paper", "scissors"]
        bot_choice = rps[randint(0, len(rps) - 1)]

        await ctx.send(
            f"You chose ***{choice.capitalize()}***."
            + f" I chose ***{bot_choice.capitalize()}***."
        )
        if bot_choice == choice:
            result = "It's a Tie!"
        elif bot_choice == rps[0]:

            def f(x):
                return {"paper": "Paper wins!", "scissors": "Rock wins!"}.get(
                    x, "Rock wins!"
                )

            result = f(choice)
        elif bot_choice == rps[1]:

            def f(x):
                return {"rock": "Paper wins!", "scissors": "Scissors wins!"}.get(
                    x, "Paper wins!"
                )

            result = f(choice)
        elif bot_choice == rps[2]:

            def f(x):
                return {"paper": "Scissors wins!", "rock": "Rock wins!"}.get(
                    x, "Scissors wins!"
                )

            result = f(choice)
        else:
            return
        if choice == "noob":
            result = "Noob wins!"
        await ctx.send(result)

    @commands.command(usage="[amount of ping]")
    async def pingme(self, ctx, amount: int = 1):
        """Ping yourself for no reason"""
        self.bot.c.execute(
            "SELECT pingme_ch FROM servers WHERE id=?", (str(ctx.guild.id),)
        )
        channel = self.bot.c.fetchall()[0][0]
        channel = self.bot.get_channel(channel)
        if not channel:
            await ctx.send("This server doesn't have channel with type `pingme`")
            return
        msg = await ctx.send("Pinging...")
        for i in range(amount):
            await asyncio.sleep(3)
            try:
                await channel.send(ctx.author.mention)
            except Forbidden:
                await ctx.send(
                    "ziBot doesn't have permission to send message inside pingme channel!"
                )
                break
        await msg.delete()

    @commands.cooldown(1, 25, commands.BucketType.user)
    @commands.command(aliases=["cfs"])
    async def classicfindseed(self, ctx):
        """Alias of `findseed classic`, Test your luck in Minecraft the classic way."""
        await ctx.invoke(self.bot.get_command("findseed classic"))

    @commands.cooldown(1, 25, commands.BucketType.user)
    @commands.group(
        aliases=["fs", "vfs", "visualfindseed", "findseedbutvisual"],
        invoke_without_command=True,
    )
    async def findseed(self, ctx):
        """Test your luck in Minecraft but visual."""
        if ctx.guild.id in self.bot.norules:
            ctx.command.reset_cooldown(ctx)

        emojis = {
            "{air}": "<:empty:754550188269633556>",
            "{frame}": "<:portal:754550231017979995>",
            "{eye}": "<:eye:754550267382333441>",
            "{end_portal}": "<:endPortal:800191496598978560>",
            "{lava}": "<a:lavaAnimated:800215203614031892>",
        }

        eyes = ["{eye}" if randint(1, 10) == 1 else "{frame}" for i in range(12)]
        eye_count = sum([1 for i in eyes if i == "{eye}"])

        # rig stuff
        # rig is capped at 12 no matter what
        rigged = {518154918276628490: 12}
        if ctx.author.id in rigged:
            rig = rigged[ctx.author.id]
            # cap rig
            if rig >= 12:
                eye_count, rig = (12,) * 2
                eyes = ["{eye}"] * 12
            elif rig <= 0:
                eye_count, rig = (0,) * 2
                eyes = ["{frame}"] * 12
            # rig loop
            while eye_count != rig:
                for i in range(len(eyes)):
                    if eye_count == rig:
                        break
                    if (
                        eyes[i] == "{frame}"
                        and randint(1, 10) == 1
                        and (eye_count < rig and eye_count != rig)
                    ):
                        eyes[i] = "{eye}"
                        eye_count += 1
                    elif eyes[i] == "{eye}" and (eye_count > rig and eye_count != rig):
                        eyes[i] = "{frame}"
                        eye_count -= 1

        # "render" portal
        sel_eye = 0
        portalframe = ""
        for row in range(5):
            for col in range(5):
                if ((col == 0 or col == 4) and (row != 0 and row != 4)) or (
                    (row == 0 or row == 4) and (col > 0 and col < 4)
                ):
                    sel_eye += 1
                    portalframe += eyes[sel_eye - 1]
                elif (col != 0 or col != 4) and (col > 0 and col < 4):
                    portalframe += "{end_portal}" if eye_count >= 12 else "{lava}"
                else:
                    portalframe += "{air}"
            portalframe += "\n"

        # replace placeholder with portal frame emoji
        for placeholder in emojis.keys():
            portalframe = portalframe.replace(placeholder, emojis[placeholder])

        e = embedDefault(
            ctx,
            author_pos="top",
            title="findseed",
            description=f"Your seed is a **{eye_count}** eye: \n\n{portalframe}",
            color=discord.Colour(0x38665E),
        )
        await ctx.send(embed=e)

    @findseed.command(name="classic")
    async def classic_findseed(self, ctx):
        """Test your luck in Minecraft the classic way."""
        if ctx.guild.id in self.bot.norules:
            ctx.command.reset_cooldown(ctx)

        rigged = {186713080841895936: 9000, 518154918276628490: 12}

        if ctx.author.id in rigged:
            totalEyes = rigged[ctx.author.id]
        else:
            totalEyes = 0
            for i in range(12):
                randomness = randint(1, 10)
                if randomness <= 1:
                    totalEyes += 1
        await ctx.send(
            f"{ctx.message.author.mention} -> your seed is a {totalEyes} eye"
        )

    @commands.cooldown(1, 25, commands.BucketType.guild)
    @commands.command()
    async def findsleep(self, ctx):
        """See how long you sleep."""
        if ctx.guild.id in self.bot.norules:
            ctx.command.reset_cooldown(ctx)

        lessSleepMsg = [
            "gn, insomniac!",
            "counting sheep didn't work? try counting chloroform vials!",
            "try a glass of water",
            "some decaf coffee might do the trick!",
        ]

        moreSleepMsg = [
            "waaakeee uuuppp!",
            "are they dead or asleep? I can't tell.",
            "wake up, muffin head",
            "psst... coffeeee \\:D",
        ]

        sleepHrs = randint(0, 24)

        if sleepHrs == 0:
            await ctx.send(
                f"{ctx.author.mention} -> your sleep is 0 hours long - nice try \:D"
            )
        elif sleepHrs <= 5:
            if sleepHrs == 1:
                s = ""
            else:
                s = "s"
            await ctx.send(
                f"{ctx.author.mention} -> your sleep is {sleepHrs} hour{s} long - {lessSleepMsg[randint(0, len(lessSleepMsg) - 1)]}"
            )
        else:
            await ctx.send(
                f"{ctx.author.mention} -> your sleep is {sleepHrs} hours long - {moreSleepMsg[randint(0, len(moreSleepMsg) - 1)]}"
            )

    @commands.command()
    @commands.check(is_redarmy)
    async def someone(self, ctx):
        """Summon random member."""
        await ctx.send(choice(ctx.guild.members).mention)

    @commands.command(aliases=["badjokes"])
    async def dadjokes(self, ctx):
        """Get random dad jokes."""
        headers = {"accept": "application/json"}
        async with self.bot.session.get(
            "https://icanhazdadjoke.com/", headers=headers
        ) as req:
            dadjoke = json.loads(await req.text())["joke"]
        e = discord.Embed(title=dadjoke, color=discord.Colour(0xFEDE58))
        e.set_author(
            name="icanhazdadjoke",
            icon_url="https://raw.githubusercontent.com/null2264/null2264/master/epicface.png",
        )
        await ctx.send(embed=e)

    @commands.cooldown(1, 25, commands.BucketType.guild)
    @commands.command(aliases=["isimposter"], usage="[impostor count] [player count]")
    async def isimpostor(self, ctx, impostor: int = 1, player: int = 10):
        """Check if you're an impostor or a crewmate."""
        if ctx.guild.id in self.bot.norules:
            ctx.command.reset_cooldown(ctx)
        if 3 < impostor < 1:
            await em_ctx_send_error("Impostor counter can only be up to 3 impostors")
            return
        chance = 100 * impostor / player / 100
        if random() < chance:
            await ctx.send(f"{ctx.author.mention}, you're a crewmate!")
        else:
            await ctx.send(f"{ctx.author.mention}, you're an impostor!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.author.bot:
            return

        fair_guilds = [
            759073367767908375,
            758764126679072788,
            745481731133669476,
            690032983817846859,
        ]
        bad_words = ["fair", "ⓕⓐⓘⓡ", "ɹıɐɟ", "justo", "adil"]
        fair = ""
        for word in bad_words:
            if word in message.content.lower().replace(" ", ""):
                fair += f"{word.title()} "
        if message.guild.id in fair_guilds and fair:
            try:
                await message.channel.send(fair)
            except UnboundLocalError:
                pass

    @commands.command()
    async def findanime(self, ctx):
        """Find a random anime picture."""
        subreddit = await self.reddit.hot("animereactionimages")
        posts = subreddit.posts
        submission = choice([post for post in posts if not post.is18])

        e = embedDefault(
            ctx,
            author_pos="bottom",
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
            if not submission.isVideo:
                e.set_image(url=submission.url)
            else:
                await ctx.send(embed=e)
                await ctx.send(submission.url)
                return

        await ctx.send(embed=e)

    @commands.command(usage="(member)")
    @commands.cooldown(5, 25, type=commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    async def triggered(self, ctx, member: discord.User = None):
        """Make your or someone else's avatar triggered."""
        if "dagpi_token" not in self.bot.config:
            return
        if not member:
            member = ctx.author
        url = "https://api.dagpi.xyz/image/triggered/?url=" + str(
            member.avatar_url_as(format="png", size=1024)
        )
        async with self.bot.session.get(
            url=url, headers={"Authorization": self.bot.config["dagpi_token"]}
        ) as res:
            image = io.BytesIO(await res.read())
            img = discord.File(fp=image, filename="triggered.gif")
            await ctx.send(file=img)

    @commands.command(usage="(status code)")
    async def httpcat(self, ctx, status_code):
        """Get http status code with cat in it."""
        async with self.bot.session.get(url=f"https://http.cat/{status_code}") as res:
            image = io.BytesIO(await res.read())
            img = discord.File(fp=image, filename="httpcat.jpg")
            await ctx.reply(file=img)

    @commands.cooldown(5, 25, type=commands.BucketType.user)
    @commands.command(aliases=["piglin"], usage="[amount of gold]", example="{prefix}barter 64")
    async def barter(self, ctx, gold: int = 64):
        """Barter with Minecraft's Piglin. (Based on JE 1.16.1, before nerf)"""
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
                "gravel": "<:gravel:807262690506047530>",
                "leather": "<:leather:807262494619860993>",
                "nether-brick": "<:netherbrick:807262738443141180>",
                "obsidian": "<:obsidian:807262809883803648>",
                "cry-obsidian": "<:cryobsidian:807262920542912562>",
                "soul-sand": "<:soulsand:807262976104464385>",
            }.get(name, "❔")

        e = embedDefault(
            ctx,
            author_pos="top",
            title="Bartering with {} gold{}".format(gold, "s" if gold > 1 else ""),
            description="You got:\n\n{}".format(
                "\n".join(["{} → {}".format(
                    emoji(v[0]), v[1]) for v in items.values()]
                )
            ),
            colour=discord.Colour.gold(),
        )
        await ctx.send(embed=e)

    @commands.command()
    async def pp(self, ctx):
        """Show your pp size."""
        pp = "8" + "=" * randint(1, 500) + "D"
        e = discord.Embed(
            title="Your pp looks like this:",
            description="`{}`".format(pp),
            colour=discord.Colour.random(),
        )
        e.set_author(
            name=f"{ctx.message.author}",
            icon_url=ctx.message.author.avatar_url,
        )
        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(Fun(bot))
