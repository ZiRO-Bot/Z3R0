"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Optional

import aiohttp


class Translated:
    __slots__ = ("source", "destination", "dest", "origin", "translated")

    def __init__(self, source, dest, origin, translated):
        self.source = source
        self.destination = dest
        self.dest = dest
        self.origin = origin
        self.translated = translated

    def __str__(self):
        return self.translated

    def __repr__(self):
        return f"<{self.source} -> {self.destination}: origin={self.origin}, translated={self.translated}>"


class GoogleTranslate:
    """Google translate wrapper that require no token/api key"""

    def __init__(self, *, session: aiohttp.ClientSession = None):
        self.session = session or aiohttp.ClientSession()

    async def translate(
        self, query: str, /, source: Optional[str] = "auto", dest: Optional[str] = "en"
    ) -> Optional[Translated]:
        # Possible endpoints:
        # - https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl=en&q=bonjour
        #   * Require browser-like user-agent
        # - https://translate.googleapis.com/translate_a/single?client=gtx&dt=t&sl=auto&tl=en&q=bonjour

        async with self.session.get(
            "https://translate.googleapis.com/translate_a/single?client=gtx&dt=t" + f"&sl={source}&tl={dest}&q={query}"
        ) as res:
            data = await res.json()
            return Translated(data[2], dest, data[0][0][1], data[0][0][0])


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    trans = GoogleTranslate()
    a = loop.run_until_complete(trans.translate("hola"))
    print(a.__repr__())
    loop.run_until_complete(trans.translate("halo", source="id"))
