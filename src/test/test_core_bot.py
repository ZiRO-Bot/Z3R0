"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import discord.ext.test as dpytest
import pytest

from zibot.core.bot import ziBot


@pytest.mark.asyncio
async def testBotMentioned(bot: ziBot):
    """Test prefix list being sent when bot is mentioned"""
    await dpytest.message(bot.user.mention)  # type: ignore
    assert not dpytest.verify().message().nothing()
