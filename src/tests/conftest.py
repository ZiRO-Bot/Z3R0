"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import aiohttp
import discord
import discord.ext.test as dpytest
import pytest
import pytest_asyncio
from discord.ext import commands

from main.core.bot import ziBot
from main.core.config import Config
from main.core.embed import ZEmbed


@pytest_asyncio.fixture
async def bot():
    Config("")
    testBot = ziBot(Config("", test=True))
    dpytest.configure(testBot)
    await testBot._async_setup_hook()
    await testBot.setup_hook()
    testBot.session = aiohttp.ClientSession(headers={"User-Agent": "Discord/Z3RO (ziBot/3.0 by ZiRO2264)"})
    return testBot


@pytest.mark.asyncio
async def testPing(bot: ziBot):
    ctx = await bot.get_context(await dpytest.message(">ping"))
    e = ZEmbed.default(ctx, title="Pong!")
    assert dpytest.verify().message().embed(e)
