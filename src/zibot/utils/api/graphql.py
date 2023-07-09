"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import aiohttp


class GraphQL:
    """
    GraphQL-based API Wrapper.

    Example:
        # Somewhere (maybe __init__)
        self.graphql = GraphQL("https://graphql.anilist.co")

        # Querying stuff (POST method)
        self.graphql.queryPost(
            '''
                query($id:Int){
                    Media(id:$id, type:ANIME){
                        id
                        format
                        title { romaji }
                        coverImage { large }
                        isAdult
                    }
                }
            ''',
            id=25,
        )
    """

    def __init__(self, baseUrl: str, **kwargs):
        self.baseUrl = baseUrl
        self.session = kwargs.pop("session", None)

    async def generateSession(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def query(self, query, /, method: str = "POST", **kwargs):
        await self.generateSession()

        async with getattr(self.session, method.lower())(self.baseUrl, json={"query": query, "variables": kwargs}) as req:
            return await req.json()

    async def queryPost(self, query, /, **kwargs):
        return await self.query(query, method="POST", **kwargs)

    async def queryGet(self, query, /, **kwargs):
        return await self.query(query, method="GET", **kwargs)


if __name__ == "__main__":
    """For testing."""
    import asyncio

    loop = asyncio.get_event_loop()
    print(
        loop.run_until_complete(
            GraphQL("https://graphql.anilist.co").queryPost(
                """
                    query($id:Int){
                        Media(id:$id, type:ANIME){
                            id
                            format
                            title { romaji }
                            coverImage { large }
                            isAdult
                        }
                    }
                """,
                id=25,
            )
        )
    )
