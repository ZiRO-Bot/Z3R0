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
from .utilities.formatting import hformat, realtime
from .utilities.paginator import ZiMenu, FunctionPageSource
from .api import anilist
from .api.anilistQuery import *
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


class AniSearchPage(FunctionPageSource):
    """
    Workaround to make `>anime search` work with ext.menus
    Might have better way to do this, but for now this will do.
    """

    def __init__(self, ctx, keyword, *, _type=None, api=None):
        super().__init__(ctx, per_page=1)
        self._type = _type
        self.api = api or anilist.AniList()
        self.keyword = keyword

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
        
        max_size = 250
        if len(desc) > max_size:
            orig_size = len(desc)
            desc,_ = desc[:max_size], desc
            new_size = orig_size - len(desc)
            desc += f"... **+{new_size} hidden**"

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


class AniList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = self.bot.logger
        self.anilist = anilist.AniList(session=self.bot.session)
        self.watchlist = self.get_raw_watchlist()
        self.handle_schedule.start()

    def get_raw_watchlist(self):
        self.bot.c.execute("SELECT * FROM ani_watchlist WHERE 1")
        server_row = self.bot.c.fetchall()
        if not server_row:
            return {}
        pre = {k[0]: k[1] or None for k in server_row}
        return {int(k): v.split(",") if v else None for (k, v) in pre.items()}

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
        for guild in self.watchlist:
            if not self.watchlist[guild]:
                continue

            # Get channel to announce the anime
            self.bot.c.execute("SELECT anime_ch FROM servers WHERE id=?", (str(guild),))

            channel = self.bot.get_channel(int(self.bot.c.fetchone()[0] or 0))
            # If channel not found (removed or not exist) then skip
            if not channel:
                continue

            # Get episode that about to air
            q = await self.anilist.request(
                scheduleQuery,
                {
                    "page": 1,
                    "amount": 50,
                    "watched": self.watchlist[guild],
                    "nextDay": timestamp,
                },
            )
            if not q:
                continue
            q = q["data"]

            # Schedule the episodes if there's any
            if q and q["Page"]["airingSchedules"]:
                for e in q["Page"]["airingSchedules"]:
                    # prevent ratelimit
                    await asyncio.sleep(2)
                    self.bot.loop.create_task(self.handle_announcement(channel, e))

            # Schedule the next page if it has more than 1 page (pageInfo.hasNextPage)
            if q["Page"]["pageInfo"]["hasNextPage"]:
                await self.scheduler(int(time.time() + (24 * 60 * 60), page + 1))

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
            title="New Release!",
            description=f"Episode {eps} of [{anime}]({data['media']['siteUrl']}) (**ID:** {_id}) has just aired.",
            colour=discord.Colour(0x02A9FF),
            timestamp=datetime.datetime.fromtimestamp(data["airingAt"]),
        )
        e.set_thumbnail(
            url=filter_image(
                channel,
                is_adult=data["media"]["isAdult"],
                image_url=data["media"]["coverImage"]["large"],
            )
        )
        e.set_author(
            name="AnilList",
            icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
        )
        e.add_field(
            name="Streaming Sites",
            value=sites or "No official stream links available",
            inline=False,
        )
        if self.bot.user.id == 733622032901603388:
            # ---- For testing only
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(e["timeUntilAiring"])
        await channel.send(embed=e)

    def set_guild_watchlist(self, guild_id, watchlist):
        if not watchlist:
            self.bot.c.execute(
                "UPDATE ani_watchlist SET anime_id=? WHERE id=?", (None, str(guild_id))
            )
            self.watchlist[guild_id] = watchlist
        else:
            self.bot.c.execute(
                "UPDATE ani_watchlist SET anime_id=? WHERE id=?",
                (watchlist, str(guild_id)),
            )
        self.bot.conn.commit()

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
        watchlist = self.watchlist
        if (
            not watchlist[int(ctx.guild.id)]
            or str(anime_id) not in watchlist[int(ctx.guild.id)]
        ):
            try:
                watchlist[int(ctx.guild.id)].append(str(anime_id))
            except AttributeError:
                watchlist[int(ctx.guild.id)] = [str(anime_id)]

            new_watchlist = ",".join(sorted(watchlist[int(ctx.guild.id)]))

            self.set_guild_watchlist(ctx.guild.id, new_watchlist)

            added = True

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
        watchlist = self.watchlist
        if str(anime_id) in watchlist[int(ctx.guild.id)]:
            watchlist[int(ctx.guild.id)].remove(str(anime_id))
            new_watchlist = ",".join(sorted(watchlist[int(ctx.guild.id)]))
            if len(watchlist) >= 2:
                self.set_guild_watchlist(ctx.guild.id, new_watchlist)
            else:
                self.set_guild_watchlist(ctx.guild.id, None)
            removed = True

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
    async def watchlist(self, ctx):
        """Get list of anime that added to watchlist."""
        embed = discord.Embed(title="Anime Watchlist", colour=discord.Colour(0x02A9FF))
        embed.set_author(
            name="AniList",
            icon_url="https://gblobscdn.gitbook.com/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png",
        )
        if not self.watchlist[ctx.guild.id]:
            embed.description = "No anime in watchlist."
            return await ctx.send(embed=embed)
        a = await self.anilist.request(
            listQ, {"mediaId": self.watchlist[ctx.guild.id]}
        )
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
                    datetime.timedelta(
                        seconds=e["nextAiringEpisode"]["timeUntilAiring"]
                    )
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
