import aiohttp
import asyncio
import dateutil.parser
import discord
import json
import requests

from discord.ext import commands, tasks
from discord.utils import get
from .utils.formatting import pformat, realtime

session = aiohttp.ClientSession()


def checklevel(cat):
    status = json.loads(
        requests.get(
            f"https://www.speedrun.com/api/v1/leaderboards/yd4ovvg1/category/{cat}"
        ).text
    )
    try:
        if status["status"] == 404:
            return True
    except KeyError:
        return False


async def worldrecord(self, ctx, category: str = "", seed_type: str = ""):
    head = {"Accept": "application/json", "User-Agent": "ziBot/0.1"}
    game = "mcbe"

    # Text formating (e.g. Any% Glitchless -> any_glitchless)
    seed_type = pformat(seed_type)
    cat = pformat(category)

    # Get seed type
    seed_typeID = None
    async with session.get(
        f"https://www.speedrun.com/api/v1/variables/5ly7759l"
    ) as url:
        sTypeVar = json.loads(await url.text())["data"]["values"]["values"]
        for _type in sTypeVar:
            if pformat(sTypeVar[_type]["label"]) == seed_type:
                seed_typeID = _type
    if not seed_typeID:
        await ctx.send("Seed type not found, please try again")
        return

    # Output formating
    wrs = {"cat": "", "platform": "", "runner": "", "link": "", "time": ""}

    # Get platforms name
    platformsVar = json.loads(
        requests.get(
            f"https://www.speedrun.com/api/v1/variables/38dj2ex8", headers=head
        ).text
    )
    platforms = platformsVar["data"]["values"]["values"]

    # Check if ILs
    level = checklevel(cat)
    if level is True:
        _type_ = "level"
        catURL = f"{cat}/9kv7jy8k"
    else:
        _type_ = "category"
        catURL = cat
    async with session.get(
        "https://www.speedrun.com/api/v1/leaderboards/yd4ovvg1/"
        + f"{_type_}/{catURL}?embed={_type_}"
    ) as url:
        try:
            catName = json.loads(await url.text())["data"][f"{_type_}"]["data"]["name"]
        except KeyError:
            await ctx.send("Category not found, please try again.")
        if level is True:
            catName += " Any%"

    # Grab and Put Category Name to embed title
    wrs["cat"] = catName
    embed = discord.Embed(title=f"World Records", colour=discord.Colour.gold())

    # Get WRs from each platforms (PC, Mobile, Console) then send to chat
    for platform in platforms:
        async with session.get(
            "https://www.speedrun.com/api/v1/leaderboards/yd4ovvg1/"
            + f"{_type_}/{catURL}?top=1"
            + f"&var-5ly7759l={seed_typeID}&var-38dj2ex8={platform}"
        ) as url:
            wr = json.loads(await url.text())
            async with session.get(
                "https://www.speedrun.com/api/v1/runs/"
                + f"{wr['data']['runs'][0]['run']['id']}"
                + "?embed=players,level,platform"
            ) as url:
                wrData = json.loads(await url.text())["data"]
        wrs["platform"] = platforms[platform]["label"]
        if wrData["players"]["data"][0]["rel"] == "guest":
            wrs["runner"] = wrData["players"]["data"][0]["names"]
        else:
            wrs["runner"] = wrData["players"]["data"][0]["names"]["international"]
        wrs["link"] = wr["data"]["runs"][0]["run"]["weblink"]
        wrs["time"] = realtime(wrData["times"]["realtime_t"])
        embed.add_field(
            name=f"{wrs['platform']}",
            value=f"{wrs['runner']} (**[{wrs['time']}]({wrs['link']})**)",
            inline=False,
        )
    embed.set_author(
        name=f"MCBE - {wrs['cat']} - {sTypeVar[seed_typeID]['label']}",
        icon_url="https://www.speedrun.com/themes/Default/1st.png",
    )
    embed.set_thumbnail(
        url="https://raw.githubusercontent.com/null2264/null2264/master/assets/mcbe.png"
    )
    await ctx.send(embed=embed)


async def pendingrun(self, ctx):
    # From mcbeDiscordBot (Steve) by MangoMan
    def getnames(player):
        if player["rel"] == "user":
            return player["names"]["international"]
        else:
            return player["name"]

    # Run Counts
    mcbe = 0
    mcbeils = 0
    mcbece = 0

    head = {"Accept": "application/json", "User-Agent": "ziBot/0.2"}
    gameIds = ["yd4ovvg1", "v1po7r76"]  # [MCBE, MCBECE Game ID]

    for idx, game in enumerate(gameIds):
        async with session.get(
            "https://www.speedrun.com/api/v1/runs?game="
            + f"{game}&status=new&max=200&embed=category,players,level&orderby=submitted",
            headers=head,
        ) as url:
            runs = json.loads(await url.text())
        for run in runs["data"]:

            # Get run's duration and link
            duration = realtime(run["times"]["realtime_t"])
            runLink = run["weblink"]

            # Get runner(s) names (also from MangoMan)
            if len(run["players"]["data"]) > 1:
                runners = [getnames(player) for player in run["players"]["data"]]
                runners = ", ".join(runners)
            else:
                runners = getnames(run["players"]["data"][0])

            # get run's type + get category name
            if run["level"]["data"]:
                cat = run["level"]["data"]["name"]
                gameType = "Individual Level"
            else:
                cat = run["category"]["data"]["name"]
                gameType = "Full Game Run"

            # if its cat ext overwrite gameType
            if idx == 1:
                gameType = "Category Extension"

            # count runs
            if gameType == "Full Game Run":
                mcbe += 1
            elif gameType == "Individual Level":
                mcbeils += 1
            else:
                mcbece += 1

            submitted = dateutil.parser.isoparse(run["submitted"])

            embed = discord.Embed(
                title=gameType,
                url=runLink,
                description=f"{cat} in `{duration}` by **{runners}**",
                color=16711680 + idx * 60,
                timestamp=submitted,
            )
            await self.bot.get_channel(741199490391736340).send(embed=embed)

    # Pending Run Stats
    total = mcbe + mcbece + mcbeils
    embed_stats = discord.Embed(
        title="Pending Run Stats",
        description=f"Full Game Runs: {mcbe}\nIndividual Level Runs: {mcbeils}\nCategory Extension Runs: {mcbece}\n**Total: {total}**",
        color=16711680 + idx * 60,
    )
    await self.bot.get_channel(741199490391736340).send(embed=embed_stats)


# Cog commands
class MCBE(commands.Cog, name="mcbe"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def pending(self, ctx):
        """Get MCBE pending runs from speedun.com."""
        async with ctx.typing():
            await self.bot.get_channel(741199490391736340).purge(limit=500)
            await pendingrun(self, ctx)

    @commands.command(
        aliases=["worldrecords"],
        usage="[category] [seed type]",
        brief="Get MCBE world records",
    )
    async def wrs(self, ctx, category: str = "any", seed_type: str = "Set Seed"):
        """Get MCBE world record runs from speedun.com.\n\
           **Example**\n\
           `>wrs "Any% Glitchless" "Set Seed"`"""
        async with ctx.typing():
            await worldrecord(self, ctx, category, seed_type)


def setup(bot):
    bot.add_cog(MCBE(bot))
