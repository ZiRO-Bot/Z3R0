"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import asyncio

import discord.ext.test as dpytest
import pytest

from main.core.bot import ziBot
from main.core.embed import ZEmbed


@pytest.mark.asyncio
async def testNothingIsEmpty(bot: ziBot):
    """Test the rest of the commands in Meta that doesn't need DB"""
    await dpytest.message(">source")
    assert not dpytest.verify().message().nothing()
    await dpytest.message(">about")
    assert not dpytest.verify().message().nothing()
    await dpytest.message(">stats")
    assert not dpytest.verify().message().nothing()


@pytest.mark.asyncio
async def testPrefixAdd(bot: ziBot):
    """Test prefix addition"""
    await dpytest.message(">prefix + !")
    assert str(dpytest.get_embed(peek=True).title).endswith("added")


@pytest.mark.asyncio
async def testPrefixUnique(bot: ziBot):
    """Test failed prefix addition (already exists)"""
    await dpytest.message(">prefix + !")
    await dpytest.message(">prefix + !")
    assert str(dpytest.get_embed(peek=True).description).endswith("exists")


@pytest.mark.asyncio
async def testPrefixFull(bot: ziBot):
    """Test failed prefix addition (full)"""
    await dpytest.message(">prefix + 1")
    await dpytest.message(">prefix + 2")
    await dpytest.message(">prefix + 3")
    await dpytest.message(">prefix + 4")
    await dpytest.message(">prefix + 5")
    await dpytest.message(">prefix + 6")
    await dpytest.message(">prefix + 7")
    await dpytest.message(">prefix + 8")
    await dpytest.message(">prefix + 9")
    await dpytest.message(">prefix + 10")
    await dpytest.message(">prefix + 11")
    await dpytest.message(">prefix + 12")
    await dpytest.message(">prefix + 13")
    await dpytest.message(">prefix + 14")
    await dpytest.message(">prefix + 15")
    await dpytest.message(">prefix + fail")
    assert "full" in str(dpytest.get_embed(peek=True).description)


@pytest.mark.asyncio
async def testPrefixRemove(bot: ziBot):
    """Test prefix removal"""
    await dpytest.message(">prefix + !")
    await dpytest.message(">prefix - !")
    assert str(dpytest.get_embed(peek=True).title).endswith("removed")


@pytest.mark.asyncio
async def testPrefixNotExists(bot: ziBot):
    """Test failed prefix removal (prefix not exists)"""
    await dpytest.message(">prefix - !")
    assert str(dpytest.get_embed(peek=True).description).endswith("exists")


@pytest.mark.asyncio
async def testPrefixList(bot: ziBot):
    """Test whether custom prefix fetched properly or not"""
    await dpytest.message(">prefix list")
    assert str(dpytest.get_embed(peek=True).description).endswith("No custom prefix.")
    await dpytest.message(">prefix + !")
    await asyncio.sleep(6)  # Cooldown, extra 1 seconds because Windows is bad and slow
    await dpytest.message(">prefix list")
    assert str(dpytest.get_embed(peek=True).description).endswith("`!`")


@pytest.mark.asyncio
async def testPing(bot: ziBot):
    """Test executing "ping" with custom prefix"""
    await dpytest.message(">prefix + !")
    msg = await dpytest.message("!ping")
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

    be = dpytest.get_embed(peek=True)

    # dpytest don't test fields for some reason
    assert all([dpytest.utils.embed_eq(e, be), all([f == be.fields[i] for i, f in enumerate(e.fields)])])
