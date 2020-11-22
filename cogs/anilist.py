import aiohttp
import asyncio
import datetime
import discord
import json
import logging
import pytz
import re
import time

from .errors.anilist import NameNotFound, NameTypeNotFound, IdNotFound
from .utils.formatting import hformat, realtime
from .utils.paginator import ZiMenu
from .utils.api import anilist
from .utils.api.anilist_query import *
from discord.ext import tasks, commands, menus
from pytz import timezone
from typing import Optional

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


def filter_image(channel, is_adult: bool, image_url: str, _type: str = "cover"):
    """
    Filter NSFW image (banner/cover)

    Parameter
    ---------
    channel
        To get discord channel info (such as is_nsfw)
    is_adult: bool
        Boolean from anilist (media.isAdult)
    image_url: str
        Url of the image (banner/cover)
    _type: str
        Type of the image, whether its banner or cover (default: "cover")
    """
    types = ["cover", "banner"]
    _type = _type.lower()
    if _type not in types:
        raise ValueError("Invalid type")
    result = ""
    if not channel.is_nsfw() and is_adult:
        result = (
            "https://raw.githubusercontent.com/null2264/null2264/master/NSFW.png"
            if _type == "cover"
            else "https://raw.githubusercontent.com/null2264/null2264/master/nsfw_banner.jpg"
        )
    else:
        if _type == "cover":
            result = image_url
        else:
            result = (
                image_url
                or "https://raw.githubusercontent.com/null2264/null2264/master/21519-1ayMXgNlmByb.jpg"
            )
    return result


class AniSearchPage(menus.PageSource):
    """
    Workaround to make `>anime search` work with ext.menus
    Might have better way to do this, but for now this will do.
    """

    def __init__(self, ctx, keyword, *, _type=None, api=None):
        self.ctx = ctx
        self._type = _type
        self.api = api or anilist.AniList()
        self.per_page = 1
        self.keyword = keyword
        self.cache = {}

    def format_anime_info(self, menu, data, is_paged=False) -> discord.Embed:
        """
        Make a discord.Embed for `>anime info|search`.

        Parameter
        ---------
        menu
            discord.ext.menus data, containing page info (such as current page number)
        data: dict
            Anime data from AniList, it should formatted dict
        is_paged: bool (default: False)
            Whether or not the result is paged
        """
        # Streaming Site
        sites = []
        for each in data["externalLinks"]:
            if str(each["site"]) in streamingSites:
                sites.append(f"[{each['site']}]({each['url']})")
        sites = " | ".join(sites)

        # Year its aired/released
        seasonYear = data["seasonYear"]
        if seasonYear is None:
            seasonYear = "Unknown"

        # Description
        desc = data["description"]
        if desc is not None:
            for d in ["</i>", "<i>", "<br>"]:
                desc = desc.replace(d, "")
        else:
            desc = "No description."

        # Messy and Ugly ratingEmoji system
        rating = data["averageScore"] or -1
        if rating >= 90:
            ratingEmoji = "😃"
        elif rating >= 75:
            ratingEmoji = "🙂"
        elif rating >= 50:
            ratingEmoji = "😐"
        elif rating >= 0:
            ratingEmoji = "😦"
        else:
            ratingEmoji = "🤔"
        e = discord.Embed(
            title=data["title"]["romaji"] + f" ({seasonYear})",
            url=f"https://anilist.co/anime/{data['id']}",
            description=f"**{data['title']['english'] or 'No english title'} (ID: `{data['id']}`)**\n"
            + desc,
            colour=discord.Colour(0x02A9FF),
        )
        maximum = self.get_max_pages()
        e.set_author(
            name=f"AniList - "
            + (f"Page {menu.current_page + 1}/{maximum} - " if is_paged else "")
            + f"{ratingEmoji} {rating}%",
            icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
        )

        # -- Filter NSFW images
        e.set_thumbnail(
            url=filter_image(
                self.ctx.channel, data["isAdult"], data["coverImage"]["large"]
            )
        )
        e.set_image(
            url=filter_image(
                self.ctx.channel, data["isAdult"], data["bannerImage"], _type="banner"
            )
        )
        # ------

        studios = []
        for studio in data["studios"]["nodes"]:
            studios.append(studio["name"])
        e.add_field(name="Studios", value=", ".join(studios) or "Unknown", inline=False)
        e.add_field(name="Format", value=data["format"].replace("_", " "))
        if str(data["format"]).lower() in ["movie", "music"]:
            if data["duration"]:
                e.add_field(name="Duration", value=realtime(data["duration"] * 60))
            else:
                e.add_field(name="Duration", value=realtime(0))
        else:
            e.add_field(name="Episodes", value=data["episodes"] or "0")
        e.add_field(name="Status", value=hformat(data["status"]))
        genres = ", ".join(data["genres"])
        e.add_field(name="Genres", value=genres or "Unknown", inline=False)
        if sites:
            e.add_field(name="Streaming Sites", value=sites, inline=False)

        return e

    async def prepare(self):
        """
        Get necessary info to start.

        Also cache the result as first page.
        """
        q = await self.api.get_anime(self.keyword, 1, _format=self._type)
        if "Page" in q:
            self.cache["1"] = q["Page"]
            self.last_page = q["Page"]["pageInfo"]["lastPage"]
            self.is_paged = True
        else:
            self.cache["1"] = q
            self.is_paged = False
            self.last_page = 1

    def is_paginating(self):
        return self.last_page > self.per_page

    def get_max_pages(self):
        return self.last_page

    async def get_page(self, page_number):
        # Since the website index don't start from 0 lets just add 1 to page_number
        page_number += 1
        # if Nth page exist in self.cache, return the it instead of getting a new one
        if str(page_number) in self.cache:
            return self.cache[str(page_number)]
        q = await self.api.get_anime(self.keyword, page_number)
        if q:
            self.cache[str(page_number)] = q["Page"]
            return self.cache[str(page_number)]

    async def format_page(self, menu, page):
        try:
            if self.is_paged is True:
                data = page["media"][0]
            else:
                data = page["Media"]
        except IndexError:
            raise anilist.AnimeNotFound

        return self.format_anime_info(
            menu,
            data,
            is_paged=True if (self.is_paged and self.is_paginating()) else False,
        )


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
        channel = self.bot.get_channel(int(self.bot.c.fetchone()[0] or 0))
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


class AniList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = self.bot.logger
        self.watchlist = {}
        self.anilist = anilist.AniList(session=self.bot.session)
        # Init but async.
        self.bot.loop.create_task(self.async_init())

    async def async_init(self):
        """
        Create table for anilist if its not exist
        and cache all the data for later.
        """

        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                # Table for anime watchlist, just like prefixes it will no longer use ',' separator
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS 
                    anime_watchlist (
                        guild_id BIGINT REFERENCES guilds(id) ON DELETE CASCADE NOT NULL,
                        anime_id BIGINT NOT NULL
                    )
                    """
                )

                pre = [
                    (i, a) for i, a in await conn.fetch("SELECT * FROM anime_watchlist")
                ]
                for k, v in pre:
                    self.watchlist[k] = self.watchlist.get(k, []) + [v]
        self.handle_schedule.start()
    
    @tasks.loop(hours=24)
    async def handle_schedule(self):
        """
        Handle anime schedule
        """
        self.logger.warning("Checking for new releases on AniList...")
        await self.scheduler(int(time.time() + (24 * 60 * 60)), 1)

    async def scheduler(self, timestamp, page):
        """
        Get anime episode that about to air and schedule it
        """
        for server in self.watchlist:
            # Get episode that about to air
            q = await query(
                scheduleQuery,
                {
                    "page": 1,
                    "amount": 50,
                    "watched": self.watchlist[server],
                    "nextDay": timestamp,
                },
            )
            if not q:
                continue
            q = q["data"]

            # TODO: Properly implement channel setting
            channel = self.bot.get_channel(777742553041862666)

            # Schedule the episodes if there's any
            if q and q["Page"]["airingSchedules"]:
                for e in q["Page"]["airingSchedules"]:
                    # prevent ratelimit
                    await asyncio.sleep(2)
                    self.bot.loop.create_task(self.handle_announcement(channel, e))

                    # if self.bot.user.id == 733622032901603388:
                    #     # ---- For testing only
                    #     await asyncio.sleep(10)
                    #     print(e)
                    # else:
                    #     await asyncio.sleep(e["timeUntilAiring"])
                    # await queueSchedule(self)
            
            # Schedule the next page if it has more than 1 page (pageInfo.hasNextPage)
            if q["Page"]["pageInfo"]["hasNextPage"]:
                await self.scheduler(
                    int(time.time() + (24 * 60 * 60), page + 1)
                )
    
    async def handle_announcement(self, channel, data):
        """
        Format and send anime announcement's embed.
        """
        anime = data["media"]["title"]["romaji"]
        _id = data["media"]["id"]
        eps = data["episode"]
        sites = []
        for site in data["media"]["externalLinks"]:
            if str(site["site"]) in streamingSites:
                sites.append(f"[{site['site']}]({site['url']})")
        sites = " | ".join(sites)

        e = discord.Embed(
            title = "New Release!", 
            description = f"Episode {eps} of [{anime}]({data['media']['siteUrl']}) (**ID:** {_id}) has just aired.",
            colour = discord.Colour(0x02A9FF),
            timestamp = datetime.datetime.fromtimestamp(data["airingAt"]),
        )
        e.set_thumbnail(url=filter_image(channel, is_adult=data["media"]["isAdult"], image_url=data["media"]["coverImage"]["large"]))
        e.set_author(name="AnilList", icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png")
        e.add_field(
            name="Streaming Sites", value=sites or "No official stream links available", inline=False
        )
        if self.bot.user.id == 733622032901603388:
            # ---- For testing only
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(e["timeUntilAiring"])
        await channel.send(embed=e)

    def get_watchlist(self):
        """
        Get schedule from database.
        {
            <guild_id>: [anime_ids, anime_ids]
        }
        """
        return self.watchlist

    def get_guild_watchlist(self, guild_id):
        """
        Get schedule from database for a specific guild.
        {
            <guild_id>: [anime_ids, anime_ids]
        }
        """
        return self.watchlist[guild_id]

    async def remove_anime_guild(self, connection, guild_id, anime_id):
        """
        Remove anime from a guild's watchlist
        """
        async with connection.transaction():
            await connection.execute(
                "DELETE FROM anime_watchlist WHERE guild_id=$1 AND anime_id=$2",
                guild_id,
                anime_id,
            )
        if guild_id in self.watchlist:
            self.watchlist[guild_id].remove(anime_id)

    async def add_anime_guild(self, connection, guild_id, anime_id):
        """
        Add anime to a guild's watchlist
        """
        async with connection.transaction():
            await connection.execute(
                "INSERT INTO anime_watchlist VALUES($1, $2)", guild_id, anime_id
            )
        if guild_id in self.watchlist:
            self.watchlist[guild_id] += [anime_id]
        else:
            self.watchlist[guild_id] = [anime_id]

    async def bulk_add_anime_guild(self, connection, guild_id, anime_ids):
        """
        Add many anime to a guild's watchlist
        """
        async with connection.transaction():
            await connection.executemany(
                "INSERT INTO anime_watchlist VALUES($1, $2)",
                [(guild_id, _id) for _id in anime_ids],
            )
        if guild_id in self.watchlist:
            self.watchlist[guild_id] += anime_ids
        else:
            self.watchlist[guild_id] = anime_ids

    def set_guild_watchlist(self, guild, watchlist):
        if not watchlist:
            self.bot.c.execute(
                "UPDATE ani_watchlist SET anime_id=? WHERE id=?", (None, guild.id)
            )
            self.bot.conn.commit()
            self.watchlist[guild.id] = watchlist
        else:
            self.bot.c.execute(
                "UPDATE ani_watchlist SET anime_id=? WHERE id=?",
                (",".join(sorted(watchlist)), str(guild.id)),
            )

    def cog_unload(self):
        self.handle_schedule.cancel()

    async def is_mainserver(ctx):
        return ctx.guild.id == 645074407244562444

    @commands.group(brief="Get information about anime from AniList.")
    async def anime(self, ctx):
        """Get information about anime from AniList"""
        pass

    @anime.command(
        aliases=["find", "info"],
        usage="(anime) [format]",
        example='{prefix}anime search "Kimi no Na Wa" Movie\n{prefix}anime info 97731',
    )
    async def search(self, ctx, anime: str, _format: str = None):
        """Find an anime."""
        if not anime:
            await ctx.send("Please specify the anime!")
            return

        try:
            menu = ZiMenu(AniSearchPage(ctx, anime, api=self.anilist, _type=_format))
            await menu.start(ctx)
        except anilist.AnimeNotFound:
            embed = discord.Embed(
                title="404 - Not Found",
                colour=discord.Colour(0x02A9FF),
                description="Anime not found!",
            )
            embed.set_author(
                name="AniList",
                icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
            )
            return await ctx.send(embed=embed)

    @anime.command(usage="(anime id|url)")
    # @commands.check(is_mainserver)
    async def watch(self, ctx, anime_id):
        """Add anime to watchlist."""
        try:
            q = await self.anilist.get_basic_info(anime_id)
            fetched_id = q["Media"]["id"]
            # fetched_id = await self.anilist.fetch_id(anime_id)
        except anilist.AnimeNotFound:
            embed = discord.Embed(
                title="404 - Not Found",
                colour=discord.Colour(0x02A9FF),
                description="Anime not found!",
            )
            embed.set_author(
                name="AniList",
                icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
            )
            return await ctx.send(embed=embed)

        added = False
        conn = await ctx.acquire()
        if (
            ctx.guild.id not in self.watchlist
            or fetched_id not in self.watchlist[ctx.guild.id]
        ):
            await self.add_anime_guild(conn, ctx.guild.id, fetched_id)
            added = True
        await ctx.release()

        # This is stupid, but for readablity sake
        if added:
            title = q["Media"]["title"]["romaji"]
            embed = discord.Embed(
                title="New anime just added!",
                description=f"**{title}** ({fetched_id}) has been added to the watchlist!",
                colour=discord.Colour(0x02A9FF),
            )
            embed.set_author(
                name="AniList",
                icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
            )
            embed.set_thumbnail(
                url=filter_image(
                    ctx.channel,
                    q["Media"]["isAdult"],
                    q["Media"]["coverImage"]["large"],
                )
            )
            await ctx.send(embed=embed)
        elif not added:
            q = await self.anilist.get_basic_info(fetched_id)
            title = q["Media"]["title"]["romaji"]
            embed = discord.Embed(
                title="Failed to add anime!",
                description=f"**{title}** ({fetched_id}) already in the watchlist!",
                colour=discord.Colour(0x02A9FF),
            )
            embed.set_author(
                name="AniList",
                icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
            )
            embed.set_thumbnail(
                url=filter_image(
                    ctx.channel,
                    q["Media"]["isAdult"],
                    q["Media"]["coverImage"]["large"],
                )
            )
            await ctx.send(embed=embed)
        else:
            return

    @anime.command(usage="(anime id|url)")
    # @commands.check(is_mainserver)
    async def unwatch(self, ctx, anime_id):
        """Remove anime to watchlist."""
        try:
            q = await self.anilist.get_basic_info(anime_id)
            fetched_id = q["Media"]["id"]
            # fetched_id = await self.anilist.fetch_id(anime_id)
        except anilist.AnimeNotFound:
            embed = discord.Embed(
                title="404 - Not Found",
                colour=discord.Colour(0x02A9FF),
                description="Anime not found!",
            )
            embed.set_author(
                name="AniList",
                icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
            )
            return await ctx.send(embed=embed)

        removed = False
        conn = await ctx.acquire()
        if (
            ctx.guild.id in self.watchlist
            and fetched_id in self.watchlist[ctx.guild.id]
        ):
            await self.remove_anime_guild(conn, ctx.guild.id, fetched_id)
            removed = True
        await ctx.release()
        
        # This is stupid, but for readablity sake
        if removed:
            title = q["Media"]["title"]["romaji"]
            embed = discord.Embed(
                title="An anime just removed!",
                description=f"**{title}** ({fetched_id}) has been removed from watchlist!",
                colour=discord.Colour(0x02A9FF),
            )
            embed.set_author(
                name="AniList",
                icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
            )
            embed.set_thumbnail(
                url=filter_image(
                    ctx.channel,
                    q["Media"]["isAdult"],
                    q["Media"]["coverImage"]["large"],
                )
            )
            await ctx.send(embed=embed)
        elif not removed:
            q = await self.anilist.get_basic_info(fetched_id)
            title = q["Media"]["title"]["romaji"]
            embed = discord.Embed(
                title="Failed to add anime!",
                description=f"**{title}** ({fetched_id}) is not exist in the watchlist!",
                colour=discord.Colour(0x02A9FF),
            )
            embed.set_author(
                name="AniList",
                icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
            )
            embed.set_thumbnail(
                url=filter_image(
                    ctx.channel,
                    q["Media"]["isAdult"],
                    q["Media"]["coverImage"]["large"],
                )
            )
            await ctx.send(embed=embed)
        else:
            return

    @anime.command(aliases=["wl", "list"])
    # @commands.check(is_mainserver)
    async def watchlist(self, ctx):
        """Get list of anime that added to watchlist."""
        embed = discord.Embed(title="Anime Watchlist", colour=discord.Colour(0x02A9FF))
        embed.set_author(
            name="AniList",
            icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
        )
        if ctx.guild.id not in self.watchlist:
            embed.description = "No anime in watchlist."
            return await ctx.send(embed=embed)
        a = await query(listQ, {"mediaId": self.watchlist[ctx.guild.id]})
        if not a:
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

        # await send_watchlist(self, ctx)
        return


def setup(bot):
    bot.add_cog(AniList(bot))
