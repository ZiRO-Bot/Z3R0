from typing import Optional
from discord.ext import commands
import discord
import asyncio
import re
import requests
import json

async def query(query: Optional[str], variables: Optional[str]):
    req = requests.post("https://graphql.anilist.co", json={'query': query, 'variables': variables}).text
    try:
        if (json.loads(req)['errors']):
            print("Error")
            return None
    except KeyError:
        return json.loads(req)

async def find_id(url):
    # if input is ID, just return it
    try:
        _id_ = int(url)
        if _id_:
            return _id_
    except ValueError:
        pass

    # regex for AniList and MyAnimeList
    regexAL = r"/anilist\.co\/anime\/(.\d*)/"
    regexMAL = r"/myanimelist\.net\/anime\/(.\d*)"
    
    # if AL link then return the id
    match = re.search(regexAL, url)
    if match:
        return match.group(1)
    
    # if MAL link get the id, find AL id out of MAL id then return the AL id
    match = re.search(regexMAL, url)
    if not match:
        return None
    q = await query("query($malId: Int){Media(idMal:$malId){id}}", {'malId': match.group(1)})
    return q['data']['Media']['id']

async def getinfo(self, ctx, other):
    mediaId = await find_id(other)
    a = await query("query($mediaId: Int){Media(id:$mediaId){id, title {romaji, english}," +
            " episodes, status, startDate {year, month, day}," + 
            " endDate {year, month, day}, genres, coverImage {large}, description}}", {'mediaId' : mediaId})
    if a is None:
        return
    a = a['data']
    desc = a['Media']['description']
    if desc is not None:
        for d in ["</i>","<i>","<br>"]:
            desc = desc.replace(d,"")
    else:
        desc = "No description."
    engTitle = a['Media']['title']['english']
    if engTitle is None:
        engTitle = "No english title."
    embed = discord.Embed(
            title = f"{a['Media']['title']['romaji']} - AniList",
            url = f"https://anilist.co/anime/{a['Media']['id']}",
            description = f"**{engTitle}**\n{desc}"
            )
    embed.set_thumbnail(url=a['Media']['coverImage']['large'])
    embed.add_field(name="Status",value=f"{a['Media']['status']}")
    embed.add_field(name="Episodes",value=f"{a['Media']['episodes']}")
    genres = ", ".join(a['Media']['genres'])
    embed.add_field(name="Genres",value=genres, inline=False)
    await ctx.send(embed=embed)
    return

class AniList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def anime(self, ctx, instruction: str="help", other: str=None):
        if instruction == "help":
            embed = discord.Embed(
                    title = f"Help with anime",
                    description = f"` {ctx.prefix}anime <instruction> <other> `",
                    colour = discord.Colour.green()
                    )
            embed.add_field(name="Command Description", value="**Instruction**: `help`\n**Other**: MyAnimeList or AniList URL/ID")
            await ctx.send(embed=embed)
            return
        if instruction == "info":
            if not other:
                return
            async with ctx.typing():
                await getinfo(self, ctx, other)

def setup(bot):
    bot.add_cog(AniList(bot))

