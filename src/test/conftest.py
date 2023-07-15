"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import aiohttp
import discord
import discord.ext.test as dpytest
import pytest_asyncio
from discord.ext.test import factories


srcPath = Path(__file__).parent.parent
sys.path.append(str(srcPath))

from zibot.core.bot import ziBot
from zibot.core.config import Config


oldMemberDict = factories.make_member_dict


def newMakeMemberDict(*args, **kwargs):
    """Temporary fix for KeyError caused by dpy v2.2"""
    res = oldMemberDict(*args, **kwargs)
    res["flags"] = 0
    return res


factories.make_member_dict = newMakeMemberDict


@pytest_asyncio.fixture  # type: ignore
async def bot():
    testBot = ziBot(Config("totally a token yup...", "sqlite://:memory:", test=True))
    testBot.session = aiohttp.ClientSession(headers={"User-Agent": "Discord/Z3RO (ziBot/3.0 by ZiRO2264)"})
    dpytest.configure(testBot)
    await testBot._async_setup_hook()
    await testBot.setup_hook()
    await testBot.on_guild_join(dpytest.get_config().guilds[0])
    testBot.i18n.set(discord.Locale.american_english)
    yield testBot
    await testBot.close()
