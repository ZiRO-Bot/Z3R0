from core import db


async def getDisabledCommands(bot, guildId):
    if bot.cache.disabled.get(guildId) is None:
        dbDisabled = await db.Disabled.filter(guild_id=guildId)

        try:
            bot.cache.disabled.extend(guildId, [c.command for c in dbDisabled])
        except ValueError:
            return []

    return bot.cache.disabled.get(guildId, [])
