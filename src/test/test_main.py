"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import aiohttp
import discord.ext.test as dpytest
import pytest
import pytest_asyncio

from main.core.bot import ziBot
from main.core.config import Config
from main.core.embed import ZEmbed


@pytest_asyncio.fixture  # type: ignore
async def bot():
    testBot = ziBot(Config("totally a token yup...", "sqlite://:memory:", test=True))
    dpytest.configure(testBot)
    await testBot._async_setup_hook()
    await testBot.setup_hook()
    testBot.session = aiohttp.ClientSession(headers={"User-Agent": "Discord/Z3RO (ziBot/3.0 by ZiRO2264)"})
    return testBot


@pytest.mark.asyncio
async def testPing(bot: ziBot):
    msg = await dpytest.message(">ping")
    ctx = await bot.get_context(msg)
    e = ZEmbed.default(ctx, title="Pong!")
    e.add_field(
        name="<a:discordLoading:857138980192911381> | Websocket",
        value="∞",
    )
    e.add_field(
        name="<a:typing:785053882664878100> | Typing",
        value="0ms",
        inline=False,
    )

    be = dpytest.get_embed()

    # dpytest don't test fields for some reason
    assert all([dpytest.utils.embed_eq(e, be), all([f == be.fields[i] for i, f in enumerate(e.fields)])])
