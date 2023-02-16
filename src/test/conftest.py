"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import aiohttp
import discord.ext.test as dpytest
import pytest_asyncio

from main.core.bot import ziBot
from main.core.config import Config


@pytest_asyncio.fixture  # type: ignore
async def bot():
    testBot = ziBot(Config("totally a token yup...", "sqlite://:memory:", test=True))
    testBot.session = aiohttp.ClientSession(headers={"User-Agent": "Discord/Z3RO (ziBot/3.0 by ZiRO2264)"})
    dpytest.configure(testBot)
    await testBot._async_setup_hook()
    await testBot.setup_hook()
    await testBot.on_guild_join(dpytest.get_config().guilds[0])
    yield testBot
    await testBot.close()
