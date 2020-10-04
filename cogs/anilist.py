import aiohttp
import asyncio
import datetime
import discord
import json
import logging
import pytz
import re
import time

from cogs.errors.anilist import NameNotFound, NameTypeNotFound, IdNotFound
from discord.ext import tasks, commands
from pytz import timezone
from typing import Optional
from utilities.formatting import hformat, realtime

session = aiohttp.ClientSession()

streamingSites = [
    "Amazon",
    "AnimeLab",
    "Crunchyroll",
    "Funimation",
    "Hidive",
    "Hulu",
    "Netflix",
    "Viz",
    "VRV",
]

scheduleQuery = """
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
"""

searchAni = """
query($name:String,$aniformat:MediaFormat,$page:Int,$amount:Int=5){
    Page(perPage:$amount,page:$page){
        pageInfo{hasNextPage, currentPage, lastPage}
        media(search:$name,type:ANIME,format:$aniformat){
            title {
                romaji, 
                english
            },
            id,
            format,
            episodes, 
            duration,
            status, 
            genres, 
            averageScore, 
            siteUrl,
            studios{nodes{name}}, 
            coverImage {large},
            bannerImage
        }
    } 
}
"""

generalQ = """
query($mediaId: Int){
    Media(id:$mediaId, type:ANIME){
        id,
        format,
        title {
            romaji, 
            english
        }, 
        episodes, 
        duration,
        status, 
        startDate {
            year, 
            month, 
            day
        }, 
        endDate {
            year, 
            month, 
            day
        }, 
        genres, 
        coverImage {
            large
        }, 
        bannerImage,
        description, 
        averageScore, 
        studios{nodes{name}}, 
        seasonYear, 
        externalLinks {
            site, 
            url
        } 
    } 
}
"""

listQ = """
query($page: Int = 0, $amount: Int = 50, $mediaId: [Int!]!) {
  Page(page: $page, perPage: $amount) {
    pageInfo {
      currentPage
      hasNextPage
    }
    media(id_in: $mediaId, type:ANIME){
        id,
        title {
            romaji,
            english
        },
        siteUrl,
        nextAiringEpisode {
            episode,
            airingAt,
            timeUntilAiring
        }
    }
  }
}
"""


async def query(query: str, variables: Optional[str]):
    if not query:
        return None
    async with session.post(
        "https://graphql.anilist.co", json={"query": query, "variables": variables}
    ) as req:
        try:
            if json.loads(await req.text())["errors"]:
                return None
        except KeyError:
            return json.loads(await req.text())


async def send_watchlist(self, ctx):
    embed = discord.Embed(title="Anime Watchlist", colour=discord.Colour(0x02A9FF))
    embed.set_author(
        name="AniList",
        icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
    )
    watchlist = self.get_watchlist()
    a = await query(listQ, {"mediaId": watchlist[ctx.guild.id]})
    if not a:
        embed.description = "No anime in watchlist."
        await ctx.send(embed=embed)
        return
    a = a["data"]
    jakarta = timezone("Asia/Jakarta")
    if not a["Page"]["media"]:
        embed.description = "No anime in watchlist."
    for e in a["Page"]["media"]:
        if e["nextAiringEpisode"]:
            status = "AIRING"
            _time_ = str(
                datetime.datetime.fromtimestamp(
                    e["nextAiringEpisode"]["airingAt"], tz=jakarta
                ).strftime("%d %b %Y - %H:%M WIB")
            )
            _timeTillAired_ = str(
                datetime.timedelta(seconds=e["nextAiringEpisode"]["timeUntilAiring"])
            )
            embed.add_field(
                name=f"{e['title']['romaji']} ({e['id']})",
                value=f"Episode {e['nextAiringEpisode']['episode']} will be aired at"
                + f" **{_time_}** (**{_timeTillAired_}**)",
                inline=False,
            )
        else:
            status = "FINISHED"
            embed.add_field(
                name=f"{e['title']['romaji']} ({e['id']})",
                value=status or "...",
                inline=False,
            )
    await ctx.send(embed=embed)


async def getschedule(self, _time_, page):
    watchlist = self.get_watchlist()
    if not watchlist:
        return
    for server in watchlist:
        # Get data from anilist for every anime that listed on watchlist
        q = await query(
            scheduleQuery,
            {
                "page": 1,
                "amount": 50,
                "watched": watchlist[int(server)],
                "nextDay": _time_,
            },
        )
        if not q:
            continue
        q = q["data"]

        # Get channel to send the releases
        self.bot.c.execute("SELECT anime_ch FROM servers WHERE id=?", (str(server),))
        channel = self.bot.c.fetchall()[0][0]
        channel = self.bot.get_channel(channel)
        if not channel:
            continue

        # If q is not empty and airingSchedules are exist, do stuff
        if q and q["Page"]["airingSchedules"]:
            # For every anime in here get the information and schedule it
            for e in q["Page"]["airingSchedules"]:
                anime = e["media"]["title"]["romaji"]
                _id = e["media"]["id"]
                eps = e["episode"]
                sites = []
                for site in e["media"]["externalLinks"]:
                    if str(site["site"]) in streamingSites:
                        sites.append(f"[{site['site']}]({site['url']})")
                sites = " | ".join(sites)
                self.logger.info(
                    f"Scheduling {e['media']['title']['romaji']} episode {e['episode']} (about to air in {str(datetime.timedelta(seconds=e['timeUntilAiring']))})"
                )
                embed_dict = {
                    "title": "New Release!",
                    "description": f"Episode {eps} of [{anime}]({e['media']['siteUrl']}) ({_id}) has just aired!",
                    "timestamp": datetime.datetime.fromtimestamp(
                        e["airingAt"]
                    ).isoformat(),
                    "color": 0x02A9FF,
                    "thumbnail": {"url": e["media"]["coverImage"]["large"]},
                    "author": {
                        "name": "AniList",
                        "icon_url": "https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
                    },
                }

                async def queueSchedule(self):
                    embed = discord.Embed.from_dict(embed_dict)
                    if sites:
                        embed.add_field(
                            name="Streaming Sites", value=sites, inline=False
                        )
                    else:
                        embed.add_field(
                            name="Streaming Sites",
                            value="No official stream links available",
                        )
                    await channel.send(embed=embed)

            if self.bot.user.id == 733622032901603388:
                # ---- For testing only
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(e["timeUntilAiring"])
            await queueSchedule(self)

        if q["Page"]["pageInfo"]["hasNextPage"]:
            await getschedule(
                self, int(time.time() + (24 * 60 * 60 * 1000 * 1) / 1000), page + 1
            )


async def find_with_name(self, ctx, anime, _type_):
    if not _type_:
        q = await query(
            "query($name:String){Media(search:$name,type:ANIME){id,"
            + "title {romaji,english}, coverImage {large}, status, episodes, averageScore, seasonYear  } }",
            {"name": anime},
        )
    else:
        _type_ = str(_type_.upper())
        q = await query(
            "query($name:String,$atype:MediaFormat){Media(search:$name,type:ANIME,format:$atype){id,"
            + "title {romaji,english}, coverImage {large}, status, episodes, averageScore, seasonYear  } }",
            {"name": anime, "atype": _type_},
        )
    try:
        return q["data"]
    except TypeError:
        if not _type_:
            raise NameNotFound
            # return "NameNotFound"
        raise NameTypeNotFound
        # return "NameTypeNotFound"


async def find_id(self, ctx, url, _type_: str = None):
    # if input is ID, just return it, else find id via name (string)
    try:
        _id_ = int(url)
        return _id_
    except ValueError:
        pass

    # regex for AniList and MyAnimeList
    regexAL = r"/anilist\.co\/anime\/(.\d*)/"
    regexMAL = r"/myanimelist\.net\/anime\/(.\d*)"

    # if AL link then return the id
    match = re.search(regexAL, url)
    if match:
        return int(match.group(1))

    # if MAL link get the id, find AL id out of MAL id then return the AL id
    match = re.search(regexMAL, url)
    if not match:
        _id_ = await find_with_name(self, ctx, url, _type_)
        return int(_id_["Media"]["id"])

    # getting ID from MAL ID
    q = await query(
        "query($malId: Int){Media(idMal:$malId){id}}", {"malId": match.group(1)}
    )
    if q is None:
        print("Error")
        await ctx.send(f"Anime with id **{url}** can't be found.")
        return None
    return int(q["data"]["Media"]["id"])


async def getinfo(self, ctx, other, _format_: str = None):
    mediaId = await find_id(self, ctx, other, _format_)
    if not mediaId:
        raise IdNotFound

    a = await query(generalQ, {"mediaId": mediaId})
    if not a:
        raise IdNotFound

    a = a["data"]
    return a


async def send_info(self, ctx, other, _format_: str = None):
    embed = discord.Embed(title="404", colour=discord.Colour(0x02A9FF))
    embed.set_author(
        name="AniList",
        icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
    )
    try:
        a = await getinfo(self, ctx, other, _format_)
    except NameNotFound:
        embed.description = f"**{other}** not found"
        await ctx.send(embed=embed)
        return None
    except NameTypeNotFound:
        embed.description = f"**{other}** with format {_format_} not found"
        await ctx.send(embed=embed)
        return None
    except IdNotFound:
        embed.description = f"Anime with id **{other}** not found"
        await ctx.send(embed=embed)
        return None

    # Streaming Site
    sites = []
    for each in a["Media"]["externalLinks"]:
        if str(each["site"]) in streamingSites:
            sites.append(f"[{each['site']}]({each['url']})")
    sites = " | ".join(sites)

    # Description
    desc = a["Media"]["description"]
    if desc is not None:
        for d in ["</i>", "<i>", "<br>"]:
            desc = desc.replace(d, "")
    else:
        desc = "No description."

    # English Title
    engTitle = a["Media"]["title"]["english"]
    if engTitle is None:
        engTitle = a["Media"]["title"]["romaji"]

    # Studio Name
    studios = []
    for studio in a["Media"]["studios"]["nodes"]:
        studios.append(studio["name"])
    studio = ", ".join(studios)

    # Year its aired/released
    seasonYear = a["Media"]["seasonYear"]
    if seasonYear is None:
        seasonYear = "Unknown"

    # Rating
    rating = a["Media"]["averageScore"] or 0
    if rating >= 90:
        ratingEmoji = "😃"
    elif rating >= 75:
        ratingEmoji = "🙂"
    elif rating >= 50:
        ratingEmoji = "😐"
    else:
        ratingEmoji = "😦"

    # Episodes / Duration
    eps = a["Media"]["episodes"]
    if eps is None:
        eps = "0"

    if a["Media"]["duration"]:
        dur = realtime(a["Media"]["duration"] * 60)
    else:
        dur = realtime(0)

    # Status
    stat = hformat(a["Media"]["status"])

    embed = discord.Embed(
        title=f"{a['Media']['title']['romaji']}",
        url=f"https://anilist.co/anime/{a['Media']['id']}",
        description=f"**{engTitle} ({seasonYear})**\n{desc}",
        colour=discord.Colour(0x02A9FF),
    )
    embed.set_author(
        name=f"AniList - {ratingEmoji} {rating}%",
        icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
    )

    if "Hentai" in a["Media"]["genres"] and ctx.channel.is_nsfw() is False:
        embed.set_thumbnail(
            url="https://raw.githubusercontent.com/null2264/null2264/master/NSFW.png"
        )
    else:
        embed.set_thumbnail(url=a["Media"]["coverImage"]["large"])

    if a["Media"]["bannerImage"]:
        if "Hentai" in a["Media"]["genres"] and ctx.channel.is_nsfw() is False:
            embed.set_image(
                url="https://raw.githubusercontent.com/null2264/null2264/master/nsfw_banner.jpg"
            )
        else:
            embed.set_image(url=a["Media"]["bannerImage"])
    else:
        embed.set_image(
            url="https://raw.githubusercontent.com/null2264/null2264/master/21519-1ayMXgNlmByb.jpg"
        )

    embed.add_field(name="Studios", value=studio, inline=False)
    if str(a["Media"]["format"]).lower() in ["movie", "music"]:
        embed.add_field(name="Duration", value=f"{dur}")
    else:
        embed.add_field(name="Episodes", value=f"{eps}")
    embed.add_field(name="Status", value=f"{stat}")
    embed.add_field(name="Format", value=a["Media"]["format"].replace("_", " "))
    genres = ", ".join(a["Media"]["genres"])
    embed.add_field(name="Genres", value=genres, inline=False)
    if sites:
        embed.add_field(name="Streaming Sites", value=sites, inline=False)
    await ctx.send(embed=embed)
    return


async def search_ani_new(self, ctx, anime, page):
    q = await query(searchAni, {"name": anime, "page": page, "amount": 1})
    if q:
        return q["data"]
    return


class AniList(commands.Cog, name="anilist"):
    def __init__(self, bot):
        self.bot = bot
        self.handle_schedule.start()
        self.logger = logging.getLogger("discord")
        self.watchlist = {}

    def get_watchlist(self):
        """
        Get schedule from database.
        {
            <guild_id>: [anime_ids, anime_ids]
        }
        """
        ids = [guild.id for guild in self.bot.guilds]
        self.bot.c.execute(
            "SELECT * FROM ani_watchlist WHERE id in ({0})".format(
                ", ".join("?" for _ in ids)
            ),
            ids,
        )
        server_row = self.bot.c.fetchall()
        pre = {k[0]: k[1] or None for k in server_row}
        watchlist = {int(k): v.split(",") if v else None for (k, v) in pre.items()}
        return watchlist

    def cog_unload(self):
        self.handle_schedule.cancel()

    async def is_mainserver(ctx):
        return ctx.guild.id == 645074407244562444

    @tasks.loop(hours=24)
    async def handle_schedule(self):
        self.logger.warning("Checking for new releases on AniList...")
        await getschedule(self, int(time.time() + (24 * 60 * 60 * 1000 * 1) / 1000), 1)

    @commands.group(brief="Get information about anime from AniList.")
    async def anime(self, ctx):
        """Get information about anime from AniList"""
        pass

    @anime.command(
        name="info", usage="(anime) [format]", brief="Get information about an anime."
    )
    async def animeinfo(self, ctx, anime, _format: str = None):
        """Get information about an anime.\n\
           **Example**\n\
           `>anime info Kimi_no_Na_Wa`\n\
           `>anime info "Koe no Katachi" Movie`"""
        if not anime:
            await ctx.send("Please specify the anime!")
        async with ctx.typing():
            await send_info(self, ctx, anime, _format)
        return

    @anime.command(aliases=["find"], usage="(anime) [format]")
    async def search(self, ctx, anime, _format: str = None):
        """Find an anime."""
        if not anime:
            await ctx.send("Please specify the anime!")
            return

        page = 1
        embed_reactions = ["◀️", "▶️", "⏹️"]

        def check_reactions(reaction, user):
            if user == ctx.author and str(reaction.emoji) in embed_reactions:
                return str(reaction.emoji)
            else:
                return False

        def create_embed(ctx, data, pageData):
            embed = None
            data = data["media"][0]
            rating = data["averageScore"] or 0
            if rating >= 90:
                ratingEmoji = "😃"
            elif rating >= 75:
                ratingEmoji = "🙂"
            elif rating >= 50:
                ratingEmoji = "😐"
            else:
                ratingEmoji = "😦"
            embed = discord.Embed(
                title=data["title"]["romaji"],
                url=f"https://anilist.co/anime/{data['id']}",
                description=f"**{data['title']['english'] or 'No english title'} ({data['id']})**\n\
                                                `{ctx.prefix}anime info {data['id']} for more info`",
                colour=discord.Colour(0x02A9FF),
            )
            embed.set_author(
                name=f"AniList - "
                + f"Page {pageData['currentPage']}/{pageData['lastPage']} - "
                + f"{ratingEmoji} {rating}%",
                icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
            )

            if "Hentai" in data["genres"] and ctx.channel.is_nsfw() is False:
                embed.set_thumbnail(
                    url="https://raw.githubusercontent.com/null2264/null2264/master/NSFW.png"
                )
            else:
                embed.set_thumbnail(url=data["coverImage"]["large"])

            if data["bannerImage"]:
                if "Hentai" in data["genres"] and ctx.channel.is_nsfw() is False:
                    embed.set_image(
                        url="https://raw.githubusercontent.com/null2264/null2264/master/nsfw_banner.jpg"
                    )
                else:
                    embed.set_image(url=data["bannerImage"])
            else:
                embed.set_image(
                    url="https://raw.githubusercontent.com/null2264/null2264/master/21519-1ayMXgNlmByb.jpg"
                )

            studios = []
            for studio in data["studios"]["nodes"]:
                studios.append(studio["name"])
            embed.add_field(
                name="Studios", value=", ".join(studios) or "Unknown", inline=False
            )
            embed.add_field(name="Format", value=data["format"].replace("_", " "))
            if str(data["format"]).lower() in ["movie", "music"]:
                if data["duration"]:
                    embed.add_field(
                        name="Duration", value=realtime(data["duration"] * 60)
                    )
                else:
                    embed.add_field(name="Duration", value=realtime(0))
            else:
                embed.add_field(name="Episodes", value=data["episodes"] or "0")
            embed.add_field(name="Status", value=hformat(data["status"]))
            genres = ", ".join(data["genres"])
            embed.add_field(name="Genres", value=genres or "Unknown", inline=False)
            return embed

        q = await search_ani_new(self, ctx, anime, 1)
        if not q:
            await ctx.send(f"No anime with keyword '{anime}' not found.")
            return
        e = create_embed(ctx, q["Page"], q["Page"]["pageInfo"])
        msg = await ctx.send(embed=e)
        for emoji in embed_reactions:
            await msg.add_reaction(emoji)

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=check_reactions, timeout=60.0
                )
            except asyncio.TimeoutError:
                break
            else:
                emoji = check_reactions(reaction, user)
                try:
                    await msg.remove_reaction(reaction.emoji, user)
                except discord.Forbidden:
                    pass
                if emoji == "◀️" and page != 1:
                    page -= 1
                    q = await search_ani_new(self, ctx, anime, page)
                    if not q:
                        pass
                    e = create_embed(ctx, q["Page"], q["Page"]["pageInfo"])
                    await msg.edit(embed=e)
                if emoji == "▶️" and q["Page"]["pageInfo"]["hasNextPage"]:
                    page += 1
                    q = await search_ani_new(self, ctx, anime, page)
                    if not q:
                        pass
                    e = create_embed(ctx, q["Page"], q["Page"]["pageInfo"])
                    await msg.edit(embed=e)
                if emoji == "⏹️":
                    # await msg.clear_reactions()
                    break

        return

    # TODO: Make watchlist per server
    @anime.command(usage="(anime) [format]")
    # @commands.check(is_mainserver)
    async def watch(self, ctx, anime, _format: str = None):
        """Add anime to watchlist."""
        if not anime:
            return
        _id_ = await find_id(self, ctx, anime, _format)

        # Get info from API
        q = await getinfo(self, ctx, anime, _format)

        title = q["Media"]["title"]["romaji"]

        watchlist = self.get_watchlist()
        if (
            not watchlist[int(ctx.guild.id)]
            or str(_id_) not in watchlist[int(ctx.guild.id)]
        ):
            try:
                watchlist[int(ctx.guild.id)].append(str(_id_))
            except AttributeError:
                watchlist[int(ctx.guild.id)] = [str(_id_)]

            new_watchlist = ",".join(watchlist[int(ctx.guild.id)])

            self.bot.c.execute(
                "UPDATE ani_watchlist SET anime_id = ? WHERE id = ?",
                (new_watchlist, str(ctx.guild.id)),
            )
            self.bot.conn.commit()

            embed = discord.Embed(
                title="New anime just added!",
                description=f"**{title}** ({_id_}) has been added to the watchlist!",
                colour=discord.Colour(0x02A9FF),
            )
        else:
            embed = discord.Embed(
                title="Failed to add anime!",
                description=f"**{title}** ({_id_}) already in the watchlist!",
                colour=discord.Colour(0x02A9FF),
            )
        embed.set_author(
            name="AniList",
            icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
        )
        embed.set_thumbnail(url=q["Media"]["coverImage"]["large"])
        await ctx.send(embed=embed)
        return

    @anime.command(usage="(anime) [format]")
    # @commands.check(is_mainserver)
    async def unwatch(self, ctx, anime, _format: str = None):
        """Remove anime to watchlist."""
        if not anime:
            return
        _id_ = await find_id(self, ctx, anime)

        # Get info from API
        q = await getinfo(self, ctx, anime, _format)

        title = q["Media"]["title"]["romaji"]

        watchlist = self.get_watchlist()
        if str(_id_) in watchlist[int(ctx.guild.id)]:
            watchlist[int(ctx.guild.id)].remove(str(_id_))
            new_watchlist = ",".join(watchlist[int(ctx.guild.id)])
            if len(watchlist) >= 2:
                self.bot.c.execute(
                    "UPDATE ani_watchlist SET anime_id = ? WHERE id = ?",
                    (new_watchlist, str(ctx.guild.id)),
                )
                self.bot.conn.commit()
            else:
                self.bot.c.execute(
                    "UPDATE ani_watchlist SET anime_id = ? WHERE id = ?",
                    (None, str(ctx.guild.id)),
                )
                self.bot.conn.commit()

            embed = discord.Embed(
                title="An anime just removed!",
                description=f"**{title}** ({_id_}) has been removed from the watchlist!",
                colour=discord.Colour(0x02A9FF),
            )
        else:
            embed = discord.Embed(
                title="Failed to remove anime!",
                description=f"**{title}** ({_id_}) is not in the watchlist!",
                colour=discord.Colour(0x02A9FF),
            )
        embed.set_author(
            name="AniList",
            icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
        )
        embed.set_thumbnail(url=q["Media"]["coverImage"]["large"])
        await ctx.send(embed=embed)
        return

    @anime.command(aliases=["wl", "list"])
    # @commands.check(is_mainserver)
    async def watchlist(self, ctx):
        """Get list of anime that added to watchlist."""
        await send_watchlist(self, ctx)
        return


def setup(bot):
    bot.add_cog(AniList(bot))
