"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import asyncio

import discord.ext.test as dpytest
import pytest
from discord.ext.commands.errors import BadFlagArgument

from main.core.bot import ziBot
from main.core.errors import DefaultError


@pytest.mark.asyncio
async def testNothingIsEmpty(bot: ziBot):
    """Test the rest of the commands in Fun"""
    # TODO: Mock http request
    # await dpytest.message(">meme")
    # assert not dpytest.verify().message().nothing()
    # await dpytest.message(">httpcat")
    # assert not dpytest.verify().message().nothing()
    # await dpytest.message(">dadjokes")
    # assert not dpytest.verify().message().nothing()
    with pytest.raises(DefaultError):
        await dpytest.message(">someone")
    await dpytest.message(">pp")
    assert not dpytest.verify().message().nothing()
    await dpytest.message(">isimpostor")
    assert not dpytest.verify().message().nothing()
    await dpytest.message(">flip")
    assert not dpytest.verify().message().nothing()
    await dpytest.message(">roll 5")
    assert not dpytest.verify().message().nothing()
    await dpytest.message(">barter")
    assert not dpytest.verify().message().nothing()


@pytest.mark.asyncio
async def testFindseedInvalidMode(bot: ziBot):
    """Test invalid findseed mode"""
    try:
        await dpytest.message(">findseed mode:urmom")
    except BadFlagArgument:
        pytest.fail("'findseed' mode should fallback to 'visual'")


@pytest.mark.asyncio
async def testRPS(bot: ziBot):
    await dpytest.message(">rps rock")
    assert not dpytest.verify().message().nothing()
    await asyncio.sleep(6)
    await dpytest.message(">rps noob")
    assert dpytest.get_message(peek=True).content.endswith("Noob wins!")


@pytest.mark.asyncio
async def testClap(bot: ziBot):
    await dpytest.message(">clap test")
    assert dpytest.get_message(peek=True).content == "test"
    await asyncio.sleep(6)
    await dpytest.message(">clap")
    assert dpytest.get_message(peek=True).content == " 👏 "
    await asyncio.sleep(6)
    await dpytest.message(">clap test test")
    assert dpytest.get_message(peek=True).content == "test 👏 test"
