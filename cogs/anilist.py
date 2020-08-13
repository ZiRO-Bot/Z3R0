import discord
import asyncio
import aiohttp
import re
import requests
import json

from formatting import hformat
from typing import Optional
from discord.ext import commands

session = aiohttp.ClientSession()

scheduleQuery = '''
query($page: Int = 0, $amount: Int = 50, $watched: [Int!]!, $nextDay: Int!) {
  Page(page: $page, perPage: $amount) {
    pageInfo {
      currentPage
      hasNextPage
    }
    airingSchedules(notYetAired: true, mediaId_in: $watched, sort: TIME, airingAt_lesser: $nextDay) {
      media {
        id
        siteUrl
        format
        duration
        episodes
        title {
          romaji
        }
        coverImage {
          large
          color
        }
        externalLinks {
          site
          url
        }
        studios(isMain: true) {
          edges {
            isMain
            node {
              name
            }
          }
        }
      }
      episode
      airingAt
      timeUntilAiring
      id
    }
  }
}
'''

async def query(query: str, variables: Optional[str]):
    if not query:
        return None
    async with session.post("https://graphql.anilist.co", json={'query': query, 'variables': variables}) as req:
        try:
            if (json.loads(await req.text())['errors']):
                return None
        except KeyError:
            return json.loads(await req.text())

async def find_id(self, ctx, url, _type_: None):
    # if input is ID, just return it, else find id via name (string)
    try:
        _id_ = int(url)
        return _id_
    except ValueError:
        _id_ = await search_ani(self, ctx, url, _type_)
        return str(_id_['Media']['id'])

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
    if q is None:
        print("Error")
        return
    return q['data']['Media']['id']

async def getinfo(self, ctx, other, _format_: str=None):
    mediaId = await find_id(self, ctx, other, _format_)
    a = await query("query($mediaId: Int){Media(id:$mediaId)" +
            "{id, title {romaji, english}, episodes, status," +
            " startDate {year, month, day}, endDate {year, month, day}," +
            " genres, coverImage {large}, description, averageScore, studios{nodes{name}}, seasonYear } }",
            {'mediaId' : mediaId})
    if a is None:
        return
    a = a['data']

    # Description
    desc = a['Media']['description']
    if desc is not None:
        for d in ["</i>","<i>","<br>"]:
            desc = desc.replace(d,"")
    else:
        desc = "No description."

    # English Title
    engTitle = a['Media']['title']['english']
    if engTitle is None:
        engTitle = a['Media']['title']['romaji']

    # Studio Name
    studios = []
    for studio in a['Media']['studios']['nodes']:
        studios.append(studio['name']) 
    studio = ", ".join(studios)

    # Year its aired/released
    seasonYear = a['Media']['seasonYear']
    if seasonYear is None:
        seasonYear = "Unknown"

    # Rating
    rating = a['Media']['averageScore']
    if rating is None:
        rating = "0"

    # Episodes
    eps = a['Media']['episodes']
    if eps is None:
        eps = "0"
    
    # Status
    stat = hformat(a['Media']['status'])

    embed = discord.Embed(
            title = f"{a['Media']['title']['romaji']} - AniList",
            url = f"https://anilist.co/anime/{a['Media']['id']}",
            description = f"**{engTitle} ({seasonYear})**\n{desc}\n\n**Studios**: {studio}",
            colour = discord.Colour(0x02A9FF)
            )
    embed.set_thumbnail(url=a['Media']['coverImage']['large'])
    embed.add_field(name="Average Score",value=f"{rating}/100",)
    embed.add_field(name="Episodes",value=f"{eps}")
    embed.add_field(name="Status",value=f"{stat}")
    genres = ", ".join(a['Media']['genres'])
    embed.add_field(name="Genres",value=genres, inline=False)
    await ctx.send(embed=embed)
    return

async def search_ani(self, ctx, anime, _type_):
    if not _type_:
        q = await query("query($name:String){Media(search:$name,type:ANIME){id," +
            "title {romaji,english}, coverImage {large}, status, episodes, averageScore, seasonYear  } }",
            {'name': anime})
    else: 
        _type_ = str(_type_.upper())
        q = await query("query($name:String,$atype:MediaFormat){Media(search:$name,type:ANIME,format:$atype){id," +
            "title {romaji,english}, coverImage {large}, status, episodes, averageScore, seasonYear  } }",
            {'name': anime,'atype': _type_})
    try:
        return q['data']
    except TypeError:
        if not type:
            await ctx.send(f"{anime} not found")
            return
        await ctx.send(f"{anime} with format {_type_} not found")
        return

async def createAnnoucementEmbed(entry: str=None, date: str=None, upNext: str=None):
    print("Not usable yet.")

class AniList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def anime(self, ctx, instruction: str="help", other: str=None, _format_: str=None):
        """**Instruction**: `help, info, search`\n**Other**: MyAnimeList or AniList URL/ID\n**Format**: Movie, TV, OVA, etc [Optional]"""
        if instruction == "help":
            embed = discord.Embed(
                    title = f"Help with anime",
                    description = f"` {ctx.prefix}anime <instruction> <other> <_format_>`",
                    colour = discord.Colour.green()
                    )
            embed.add_field(name="Command Description", value=f"{ctx.command.help}")
            await ctx.send(embed=embed)
            return
        if instruction == "info":
            if not other:
                return
            async with ctx.typing():
                await getinfo(self, ctx, other, _format_)
            return
        if instruction == "search" or instruction == "find":
            if not other:
                return
            async with ctx.typing():
                q = await search_ani(self, ctx, other, _format_)
                embed = discord.Embed(
                        title = f"AniList Search - {q['Media']['title']['romaji']} (ID. {q['Media']['id']})",
                        url = f"https://anilist.co/anime/{q['Media']['id']}",
                        description = f"**{q['Media']['title']['english']} ({q['Media']['seasonYear']})**",
                        colour = discord.Colour(0x02A9FF)
                        )
                embed.set_thumbnail(url=q['Media']['coverImage']['large'])
                embed.add_field(name="Average Score",value=f"{q['Media']['averageScore']}/100",)
                embed.add_field(name="Episodes",value=f"{q['Media']['episodes']}")
                embed.add_field(name="Status",value=f"{q['Media']['status']}")
                await ctx.send(embed=embed)
                return
            return
        if instruction == "watch":
            await ctx.send("This command is not available yet.")
            return
        await ctx.send(f"There's no command called '{instruction}'!")
        return

def setup(bot):
    bot.add_cog(AniList(bot))

