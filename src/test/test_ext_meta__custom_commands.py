"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import discord.ext.test as dpytest
import pytest

from main.core.bot import ziBot
from main.exts.meta._errors import CCommandAlreadyExists, CCommandNotFound


@pytest.mark.asyncio
async def testCommandCreate(bot: ziBot):
    """Test command creation"""
    await dpytest.message(">cmd + test test")
    assert str(dpytest.get_embed(peek=True).title).endswith("created")


@pytest.mark.asyncio
async def testCommandCreateDuplicate(bot: ziBot):
    """Test failed command creation (already exists)"""
    await dpytest.message(">cmd + test test")
    with pytest.raises(CCommandAlreadyExists):
        await dpytest.message(">cmd + test test")


@pytest.mark.asyncio
async def testCommandRemove(bot: ziBot):
    """Test command removal"""
    await dpytest.message(">cmd + test test")
    await dpytest.message(">cmd - test")
    assert str(dpytest.get_embed(peek=True).title).endswith("removed")


@pytest.mark.asyncio
async def testCommandRemoveNotExists(bot: ziBot):
    """Test failed command removal (doesn't exists)"""
    with pytest.raises(CCommandNotFound) as excinfo:
        await dpytest.message(">cmd - test")


@pytest.mark.asyncio
async def testCommandPriorityExecution(bot: ziBot):
    """Test custom command execution priority"""
    await dpytest.message(">cmd + ping Test")

    await dpytest.message(">>ping")
    assert dpytest.verify().message().content("Test")

    await dpytest.message(">!ping")
    assert dpytest.verify().message().content("Test")

    await dpytest.message(">ping")
    assert not dpytest.verify().message().content("Test")
