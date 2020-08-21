import asyncio
import datetime
import discord
import os
import praw
import re

from discord.ext import commands
from random import randint
from dotenv import load_dotenv

try:
    REDDIT_CLIENT_ID = os.environ['REDDIT_CLIENT_ID']
except: 
    load_dotenv()
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")

try: 
    REDDIT_CLIENT_SECRET = os.environ['REDDIT_CLIENT_SECRET']
except: 
    load_dotenv()
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")

try: 
    REDDIT_USER_AGENT = os.environ['REDDIT_USER_AGENT']
except: 
    load_dotenv()
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                     client_secret=REDDIT_CLIENT_SECRET,
                     user_agent=REDDIT_USER_AGENT)

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 5)
    async def flip(self, ctx):
        """Flip a coin."""
        coin_side = ['heads', 'tails']
        await ctx.send(f"{ctx.message.author.mention} {coin_side[randint(0, 1)]}")

    @flip.error
    async def flip_handler(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            bot_msg = await ctx.send(f"{ctx.message.author.mention}, slowdown bud!")
            await asyncio.sleep(round(error.retry_after))
            await bot_msg.delete()

    @commands.command(usage="[number of dice]")
    @commands.cooldown(1, 5)
    async def roll(self, ctx, number: int=1):
        """Roll the dice."""
        dice = []
        for i in range(number):
            dice.append(int(randint(1,6)))
        dice = ", ".join(str(i) for i in dice)
        await ctx.send(f"{ctx.message.author.mention} just rolled {dice}!")

    @roll.error
    async def roll_handler(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            bot_msg = await ctx.send(f"{ctx.message.author.mention},"
                                       + " slowdown bud!")
            await asyncio.sleep(round(error.retry_after))
            await bot_msg.delete()

    @commands.command()
    async def meme(self, ctx):
        """Get memes from subreddit r/memes."""
        # meme_channel = self.bot.get_channel(746177519786393741)
        # --- Testing Server
        meme_channel = self.bot.get_channel(746200581152178307)
        meme_subreddits = ['memes', 
                           'PewdiepieSubmissions', 
                           'funny']
        reg_img = r".*/(i)\.redd\.it"

        if ctx.channel is not meme_channel:
            async with ctx.typing():
                await ctx.send(f"Please do this command on {meme_channel.mention}")
                return
        async with meme_channel.typing():
            selected_subreddit = meme_subreddits[randint(0,
                                                 len(meme_subreddits)-1)]
            memes_submissions = reddit.subreddit(selected_subreddit).hot()
            post_to_pick = randint(1, 50)
            for i in range(0, post_to_pick):
                submission = next(x for x in memes_submissions if not x.stickied)
            if submission.over_18:
                return
            embed = discord.Embed(title=f"r/{selected_subreddit} "
                                         + f"- {submission.title}",
                                  colour=discord.Colour(0xFF4500))
            embed.set_author(name="Reddit",
                             icon_url="https://www.redditstatic.com/desktop2x/" 
                                      + "img/favicon/android-icon-192x192.png")
            match = re.search(reg_img, submission.url)
            embed.add_field(name="Upvotes", value=submission.score)
            embed.add_field(name="Comments", value=submission.num_comments)
            if match:
                embed.set_image(url=submission.url)
            else:
                await meme_channel.send(embed=embed)
                await meme_channel.send(submission.url)
                return
            await meme_channel.send(embed=embed)

def setup(bot):
    bot.add_cog(Fun(bot))

