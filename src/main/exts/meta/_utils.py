"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from ...core import db


async def getDisabledCommands(bot, guildId):
    if bot.cache.disabled.get(guildId) is None:
        dbDisabled = await db.Disabled.filter(guild_id=guildId)

        try:
            bot.cache.disabled.extend(guildId, [c.command for c in dbDisabled])
        except ValueError:
            return []

    return bot.cache.disabled.get(guildId, [])
