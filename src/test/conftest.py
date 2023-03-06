"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import discord.ext.test as dpytest
import pytest

from src.main.core.bot import ziBot
from src.main.core.config import Config


@pytest.fixture
async def bot():
    testBot = ziBot(Config("", ""))
    dpytest.configure(testBot)
    testGuild = dpytest.backend.make_guild("Test Guild")
    dpytest.backend.make_text_channel("general", testGuild)
    dpytest.backend.make_text_channel("testing", testGuild)
    testUser = dpytest.backend.make_user("ZiRO2264", "9986")
    dpytest.backend.make_member(testUser, testGuild, "null2264")


@pytest.mark.asyncio
async def testPing(bot):
    ...
