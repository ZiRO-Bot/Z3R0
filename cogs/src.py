from discord.ext import commands, tasks
from discord.utils import get
from datetime import timedelta
import discord
import requests
import json
import asyncio
import dateutil.parser

def checklevel(cat):
    if json.loads(requests.get(f"https://www.speedrun.com/api/v1/categories/{cat}").text)['status'] == '404':
        # IDK WHY THE FUCK 404 IS STRING BUT SURE PYTHON -_-
        return True
    return False

async def worldrecord(self, ctx, category: str="Any"):
    head = {"Accept": "application/json", "User-Agent": "ziBot/0.1"}
    game = "mcbe"
    cat = category
    wrs = {
            'cat': '',
            'platform': '',
            'runner': '',
            'link': '',
            'time': ''
            }
    platformsVar = json.loads(requests.get(
            f"https://www.speedrun.com/api/v1/variables/38dj2ex8",
            headers=head).text)
    platforms = platformsVar['data']['values']['choices']

    level = checklevel(cat)
    if not level:
        catName = json.loads(requests.get(
            f"https://www.speedrun.com/api/v1/leaderboards/yd4ovvg1/category/{cat}?embed=category",
            headers=head).text)['data']['category']['data']['name']
    else:
        catName = "Any% " + json.loads(requests.get(
            f"https://www.speedrun.com/api/v1/leaderboards/yd4ovvg1/level/{cat}/9kv7jy8k?embed=level",
            headers=head).text)['data']['level']['data']['name']
    
    wrs['cat']=catName
    embed = discord.Embed(
            title=f"{wrs['cat']} MCBE World Records",
            colour=discord.Colour.gold()
            )
    for platform in platforms:
        if not level:
            wr = json.loads(requests.get(
                "https://www.speedrun.com/api/v1/leaderboards/"+
                f"{game}/category/{cat}?top=1&var-38dj2ex8={platform}",
                headers=head).text)
        else:
            wr = json.loads(requests.get(
                "https://www.speedrun.com/api/v1/leaderboards/"+
                f"{game}/level/{cat}/9kv7jy8k?top=1&var-38dj2ex8={platform}",
                headers=head).text)
        wrData = json.loads(requests.get(
                "https://www.speedrun.com/api/v1/runs/"+
                f"{wr['data']['runs'][0]['run']['id']}"+
                "?embed=players,level,platform",
                headers=head).text)['data']
        wrs['platform']=platforms[platform]
        if wrData['players']["data"][0]['rel'] == 'guest':
            wrs['runner']=wrData['players']['data'][0]['names']
        else:
            wrs['runner']=wrData['players']["data"][0]["names"]["international"]
        wrs['link']=wrData['weblink']
        wrs['time']=timedelta(seconds=wrData['times']['realtime_t'])
        embed.add_field(name=f"{wrs['platform']}",value=f"{wrs['runner']} ({wrs['time']})",inline=False)
    await ctx.send(embed=embed)

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
    total = mcbe_runs + mcbece_runs + mcbeil_runs
    embed_stats = discord.Embed(
                title='Pending Run Stats',
                description=
                f"Full Game Runs: {mcbe_runs}\nIndividual Level Runs: {mcbeil_runs}\nCategory Extension Runs: {mcbece_runs}\n**Total: {total}**",
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
    async def wrs(self, ctx, category: str="any"):
        """Get world record runs from speedun.com
        `NOTE: type the category without '%' (e.g. >wrs Any)`"""
        async with ctx.typing():
            await worldrecord(self, ctx, category)

def setup(bot):
    bot.add_cog(Src(bot))
