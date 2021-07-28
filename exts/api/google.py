"""
Web scrapper for google search
"""


import aiohttp
import bs4
import re


from contextlib import suppress
from core.decorators import in_executor  # type: ignore
from typing import Any, Optional, List
from urllib.parse import quote_plus


class SearchResult:
    def __init__(self, link: str, title: str, contents: List[str]) -> None:
        self.link: str = link
        self.title: str = title
        self.contents: List[str] = contents

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} link={self.link} title={self.title} contents={self.contents}>"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, SearchResult) and (
            self.title == other.title and self.contents == other.contents
        )


class SpecialResult:
    def __init__(self, type: str, content: Any) -> None:
        self.type: str = type
        self.content: Any = content
        pass


class ComplementaryResult:
    def __init__(
        self, title: str, subtitle: str, description: Optional[str], info: List[tuple]
    ) -> None:
        self.title: str = title
        self.subtitle: str = subtitle
        self.description: Optional[str] = description
        self.info: List[tuple] = info

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} title={self.title} subtitle={self.subtitle} description={self.description} info={self.info}>"


class Google:
    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        self.session: Optional[aiohttp.ClientSession] = session
        self._fmt: str = (
            "https://www.google.com/search?q={query}&safe={safe}&num={num}&hl={hl}"
        )

    async def generateSession(self) -> None:
        self.session = aiohttp.ClientSession()

    @in_executor()
    def parseResults(self, page: str) -> Optional[dict]:
        soup = bs4.BeautifulSoup(page, "html.parser")

        # eg. "About N results (N seconds)"
        try:
            searchStats: str = soup.find(attrs={"id": "result-stats"}).text  # type: ignore # pyright really don't like bs4
        except AttributeError:
            return None

        # normal results
        results = soup.find("div", {"id": "search"}).find_all("div", {"class": "g"})  # type: ignore
        webRes: Optional[List[SearchResult]] = None
        specialRes: Optional[SpecialResult] = None
        # parse both webRes and specialRes (if there is)
        if results:
            webRes = []
            for result in results:
                try:
                    link = result.find("a", href=True)["href"]  # type: ignore
                except (KeyError, TypeError):
                    continue
                try:
                    title = result.find("h3").text  # type: ignore
                except AttributeError:
                    # Special result such as Currency converter, Maps, etc
                    type = result.find("h2").text  # type: ignore

                    if type == "Currency converter":
                        contents = result.find(  # type: ignore
                            "div", id=re.compile("knowledge-currency")
                        ).contents
                        formattedContent = []

                        # Currency stuff
                        convertion = contents[0].find_all("div")
                        target = f"`{convertion[0].text}`"
                        dest = convertion[1].find_all("span")
                        dest = f"**`{dest[0].text}` {dest[1].text}**"
                        formattedContent.extend([target, dest])

                        # Last updated
                        formattedContent.append(contents[1].text)
                        specialRes = SpecialResult(type, formattedContent)

                        continue
                else:
                    summary = result.find("div").select("div > span")  # type: ignore
                    if summary and title and link:
                        res = SearchResult(link, title, [s.text for s in summary[1:]])
                        if res not in webRes:
                            webRes.append(res)

        # Complementary results
        complementaryRes = soup.find("div", {"id": "rhs", "data-hveid": True})
        if complementaryRes:
            title: Optional[str] = None
            subtitle: Optional[str] = None
            desc: Optional[str] = None

            with suppress(AttributeError):
                title = complementaryRes.find("h2", {"data-attrid": "title"}).span.text  # type: ignore
                subtitle = complementaryRes.find("div", {"data-attrid": "subtitle"}).span.text  # type: ignore

            with suppress(AttributeError):
                desc = complementaryRes.find("div", {"class": "kno-rdesc"}).span.text  # type: ignore

            infoList = complementaryRes.find_all("div", {"data-attrid": True, "lang": True})  # type: ignore
            formattedInfo = []
            for info in infoList:
                span = info.find_all("span")  # type: ignore
                infoTitle = ""
                infoContent = ""
                for s in span:
                    if s.a and "fl" not in s.a.get("class", []):
                        continue
                    text = str(s.text)
                    if text.endswith(": "):
                        infoTitle = text
                        continue
                    infoContent += text
                if infoTitle and infoContent:
                    formattedInfo.append((infoTitle, infoContent))

            # A complementary result always have title and subtitle
            if subtitle and title:
                complementaryRes = ComplementaryResult(
                    title, subtitle, desc, formattedInfo
                )
            else:
                complementaryRes = None

        return {
            "stats": searchStats,
            "web": webRes,
            "complementary": complementaryRes,
            "special": specialRes,
        }

    async def search(
        self,
        query: str,
        /,
        *,
        safeSearch: bool = True,
        numberOfResult: int = 10,
        languageCode: str = "en",
    ):
        safe: str = "active" if safeSearch else "images"
        if not self.session:
            await self.generateSession()

        async with self.session.get(  # type: ignore
            self._fmt.format(
                query=query, safe=safeSearch, num=numberOfResult, hl=languageCode
            ),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36"
                )
            },
        ) as resp:
            html = await resp.text()
            return await self.parseResults(html)  # type: ignore # executor makes it awaitable
