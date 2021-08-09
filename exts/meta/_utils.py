async def getDisabledCommands(bot, guildId):
    if bot.cache.disabled.get(guildId) is None:
        dbDisabled = await bot.db.fetch_all(
            "SELECT command FROM disabled WHERE guildId=:id", values={"id": guildId}
        )
        try:
            bot.cache.disabled.extend(guildId, [c[0] for c in dbDisabled])
        except ValueError:
            return []
    return bot.cache.disabled.get(guildId, [])
