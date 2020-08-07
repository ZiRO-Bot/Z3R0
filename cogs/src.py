from discord.ext import commands, tasks
from discord.utils import get
from datetime import timedelta
import discord
import requests
import json
import asyncio
import dateutil.parser

async def pendingrun(self, ctx):
    mcbe_runs = 0
    mcbeil_runs = 0
    mcbece_runs = 0
    head = {"Accept": "application/json", "User-Agent": "ziBot/0.1"}
    gameID = 'yd4ovvg1' # MCBE's gameid
    gameID2 = 'v1po7r76' # MCBE CE's gameid
    runsRequest = requests.get(
            f'https://www.speedrun.com/api/v1/runs?game={gameID}&status=new&max=200&embed=category,players,level&orderby=submitted',
            headers=head)
    runs = json.loads(runsRequest.text)
    runsRequest2 = requests.get(
            f'https://www.speedrun.com/api/v1/runs?game={gameID2}&status=new&max=200&embed=category,players,level&orderby=submitted',
            headers=head)
    runs2 = json.loads(runsRequest2.text)

    for game in range(2):
        for i in range(200):
            leaderboard = ''
            level = False
            try:
                for key, value in runs['data'][i].items():
                    if key == 'id':
                        run_id = value
                    if key == 'weblink':
                        link = value
                    if key == 'level':
                        if value['data']:
                            level = True
                            categoryName = value['data']['name']
                    if key == 'category' and not level:
                        categoryName = value["data"]["name"]
                    if key == 'players':
                        if value["data"][0]['rel'] == 'guest':
                            player = value["data"][0]['name']
                        else:
                            player = value["data"][0]["names"]["international"]
                    if key == 'times':
                        rta = timedelta(seconds=value['realtime_t'])
                    if key == 'submitted':
                        timestamp = dateutil.parser.isoparse(value)
            except IndexError:
                break
            if game == 0:
                if level is True:
                    mcbeil_runs += 1
                    leaderboard = 'Individual Level Run'
                else:
                    mcbe_runs += 1
                    leaderboard = "Full Game Run"
            elif game == 1:
                leaderboard = "Category Extension Run"
                mcbece_runs += 1
            embed = discord.Embed(
                        title=leaderboard,
                        url=link,
                        description=
                        f"{categoryName} in `{str(rta).replace('000','')}` by **{player}**",
                        color=16711680 + i * 60,
                        timestamp=timestamp)
            await self.bot.get_channel(741199490391736340).send(embed=embed)
    runs = runs2
    gameID = gameID2
    embed_stats = discord.Embed(
                title='Pending Run Stats',
                description=
                f"Full Game Runs: {mcbe_runs}\nIndividual Level Runs: {mcbeil_runs}\nCategory Extension Runs: {mcbece_runs}",
                color=16711680 + i * 60)
    await self.bot.get_channel(741199490391736340).send(embed=embed_stats)

class Src(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def pending(self, ctx):
        """Get pending runs from speedun.com"""
        async with ctx.typing():
            await self.bot.get_channel(741199490391736340).purge(limit=500)
            await pendingrun(self, ctx)
    
    @commands.command()
    async def wrs(self, ctx):
        """Get world record runs from speedun.com"""
        await ctx.send("Not available yet.")

def setup(bot):
    bot.add_cog(Src(bot))
