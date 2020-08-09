from discord.ext import commands, tasks
from formatting import pformat, realtime
from discord.utils import get
from datetime import timedelta
import aiohttp
import discord
import requests
import json
import asyncio
import dateutil.parser

session = aiohttp.ClientSession()

def checklevel(cat):
    status = json.loads(requests.get(f"https://www.speedrun.com/api/v1/leaderboards/yd4ovvg1/category/{cat}").text)
    try:
        if status['status'] == 404:
            return True
    except KeyError:
        return False

async def worldrecord(self, ctx, category: str="", seed_type: str=""):
    head = {"Accept": "application/json", "User-Agent": "ziBot/0.1"}
    game = "mcbe"

    # Text formating (e.g. Any% Glitchless -> any_glitchless)
    seed_type=pformat(seed_type)
    cat = pformat(category)

    # Get seed type
    seed_typeID = None
    async with session.get(f"https://www.speedrun.com/api/v1/variables/5ly7759l") as url:
        sTypeVar = json.loads(await url.text())['data']['values']['values']
        for _type in sTypeVar:
            if pformat(sTypeVar[_type]['label']) == seed_type:
                seed_typeID = _type
    if not seed_typeID:
        await ctx.send("Seed type not found, please try again")
        return 

    # Output formating
    wrs = {
            'cat': '',
            'platform': '',
            'runner': '',
            'link': '',
            'time': ''
            }

    # Get platforms name
    platformsVar = json.loads(requests.get(
            f"https://www.speedrun.com/api/v1/variables/38dj2ex8",
            headers=head).text)
    platforms = platformsVar['data']['values']['values']

    # Check if ILs
    level = checklevel(cat)
    if level is True:
        _type_ = 'level'
        catURL = f'{cat}/9kv7jy8k'
    else:
        _type_ = 'category'
        catURL = cat
    async with session.get("https://www.speedrun.com/api/v1/leaderboards/yd4ovvg1/" + 
            f"{_type_}/{catURL}?embed={_type_}") as url:
        try:
            catName = json.loads(await url.text())['data'][f'{_type_}']['data']['name']
        except KeyError:
            await ctx.send("Category not found, please try again.")
        if level is True:
            catName += " Any%"

    # Grab and Put Category Name to embed title
    wrs['cat']=catName
    embed = discord.Embed(
            title=f"MCBE {wrs['cat']} {sTypeVar[seed_typeID]['label']} World Records",
            colour=discord.Colour.gold()
            )

    # Get WRs from each platforms (PC, Mobile, Console) then send to chat
    for platform in platforms:
        async with session.get("https://www.speedrun.com/api/v1/leaderboards/yd4ovvg1/" + 
                f"{_type_}/{catURL}?top=1" + 
                f"&var-5ly7759l={seed_typeID}&var-38dj2ex8={platform}") as url:
            wr = json.loads(await url.text())
            async with session.get("https://www.speedrun.com/api/v1/runs/"+
                f"{wr['data']['runs'][0]['run']['id']}"+
                "?embed=players,level,platform") as url:
                wrData = json.loads(await url.text())['data']
        wrs['platform']=platforms[platform]['label']
        if wrData['players']["data"][0]['rel'] == 'guest':
            wrs['runner']=wrData['players']['data'][0]['names']
        else:
            wrs['runner']=wrData['players']["data"][0]["names"]["international"]
        wrs['link']=wrData['weblink']
        wrs['time']=realtime(wrData['times']['realtime_t'])
        embed.add_field(name=f"{wrs['platform']}",value=f"{wrs['runner']} ({wrs['time']})",inline=False)
    await ctx.send(embed=embed)

async def pendingrun(self, ctx):
    mcbe_runs = 0
    mcbeil_runs = 0
    mcbece_runs = 0
    head = {"Accept": "application/json", "User-Agent": "ziBot/0.1"}
    gameID = ['yd4ovvg1', 'v1po7r76'] #[MCBE, MCBECE Game ID]
    run = {
            'id': '',
            'link': '',
            'categoryName': '',
            'runner': '',
            'time': '',
            'submit_time': '',
            'leaderboard': ''
            }
    for game in range(2):
        async with session.get('https://www.speedrun.com/api/v1/runs?game=' + 
                f'{gameID[game]}&status=new&max=200&embed=category,players,level&orderby=submitted') as url:
            runs = json.loads(await url.text())
        for i in range(200):
            try:
                leaderboard = ''
                level = False
                run_item = runs['data'][i]
                run['id'] = run_item['id']
                run['link'] = run_item['weblink']
                # Cat Name (ILs or Not)
                if run_item['level']['data']:
                    level = True
                    run['categoryName'] = run_item['level']['data']['name']
                elif not level:
                    run['categoryName'] = run_item['category']['data']['name']
                # Runner Name
                if run_item['players']['data'][0]['rel'] == 'guest':
                    run['runner'] = run_item['players']['data'][0]['name']
                else:
                    run['runner'] = run_item['players']['data'][0]['names']['international']
                run['time'] = timedelta(seconds=run_item['times']['realtime_t'])
                run['submit_time'] = dateutil.parser.isoparse(run_item['submitted'])
                if game == 0:
                    if level is True:
                        mcbeil_runs += 1
                        run['leaderboard'] = 'Individual Level Run'
                    else:
                        mcbe_runs += 1
                        run['leaderboard'] = "Full Game Run"
                elif game == 1:
                    mcbece_runs += 1
                    run['leaderboard'] = 'Category Extension Run'
                embed = discord.Embed(
                            title=run['leaderboard'],
                            url=run['link'],
                            description=
                            f"{run['categoryName']} in `{str(run['time']).replace('000','')}` by **{run['runner']}**",
                            color=16711680 + i * 60,
                            timestamp=run['submit_time'])
                await self.bot.get_channel(741199490391736340).send(embed=embed)
            except IndexError:
                break
    total = mcbe_runs + mcbece_runs + mcbeil_runs
    embed_stats = discord.Embed(
                title='Pending Run Stats',
                description=
                f"Full Game Runs: {mcbe_runs}\nIndividual Level Runs: {mcbeil_runs}\nCategory Extension Runs: {mcbece_runs}\n**Total: {total}**",
                color=16711680 + i * 60)
    await self.bot.get_channel(741199490391736340).send(embed=embed_stats)

# Cog commands
class Src(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def pending(self, ctx):
        """Get pending runs from speedun.com"""
        async with ctx.typing():
            await self.bot.get_channel(741199490391736340).purge(limit=500)
            await pendingrun(self, ctx)
    
    @commands.command(aliases=["worldrecords"])
    async def wrs(self, ctx, category: str="any", seed_type: str="Set Seed"):
        """Get mcbe world record runs from speedun.com
        `e.g. >wrs "Any% Glitchless" "Set Seed"`"""
        async with ctx.typing():
            await worldrecord(self, ctx, category, seed_type)

def setup(bot):
    bot.add_cog(Src(bot))
