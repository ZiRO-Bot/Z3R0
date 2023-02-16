"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import discord.ext.test as dpytest
import pytest

from main.core.bot import ziBot
from main.core.embed import ZEmbed


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


@pytest.mark.asyncio
async def testPrefixAdd(bot: ziBot):
    await dpytest.message(">prefix + !")
    assert str(dpytest.get_embed(peek=True).title).endswith("added")


@pytest.mark.asyncio
async def testPrefixUnique(bot: ziBot):
    await dpytest.message(">prefix + !")
    await dpytest.message(">prefix + !")
    assert str(dpytest.get_embed(peek=True).description).endswith("exists")


@pytest.mark.asyncio
async def testPrefixFull(bot: ziBot):
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
async def testPrefixNotExists(bot: ziBot):
    await dpytest.message(">prefix - !")
    assert str(dpytest.get_embed(peek=True).description).endswith("exists")
