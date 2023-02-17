"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import discord.ext.test as dpytest
import pytest
from discord.ext.commands.errors import BadLiteralArgument

from main.core.bot import ziBot


@pytest.mark.asyncio
async def testFindseedInvalidMode(bot: ziBot):
    """Test invalid findseed mode"""
    try:
        await dpytest.message(">findseed mode:urmom")
    except BadLiteralArgument:
        pytest.fail("'findseed' mode should fallback to 'visual'")
