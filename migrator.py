"""
Simple migrator tool

Migrate from 2.0 database scheme to 3.0 database scheme
Coded for SQLite -> SQLite migration

WARNING: This script coded to be run once,
running it multiple time may broke something
"""

import asyncio

from databases import Database

from exts.utils import dbQuery

OLD_DB = Database("sqlite:///data/database2_0.db")
NEW_DB = Database("sqlite:///data/database3_0.db")
DEF_PREFIX = ">"


async def prepareNewDB():
    await NEW_DB.connect()
    async with NEW_DB.transaction():
        # core/bot.py
        await NEW_DB.execute(dbQuery.createGuildsTable)
        await NEW_DB.execute(dbQuery.createGuildConfigsTable)
        await NEW_DB.execute(dbQuery.createGuildChannelsTable)
        await NEW_DB.execute(dbQuery.createGuildRolesTable)
        await NEW_DB.execute(dbQuery.createPrefixesTable)
        await NEW_DB.execute(dbQuery.createDisabledTable)
        # exts/timer.py
        await NEW_DB.execute(dbQuery.createTimerTable)
        # exts/meta.py
        await NEW_DB.execute(dbQuery.createCommandsTable)
        await NEW_DB.execute(dbQuery.createCommandsLookupTable)


async def migrateGuildData():
    """Migrate guild id, prefixes and channels"""
    data = await OLD_DB.fetch_all("SELECT * FROM servers")

    guilds = []
    prefixes = []
    channels = []
    for i in data:
        guildId = i[0]
        i = i[1:]
        guilds.append({"id": int(guildId)})

        if i[0] is not None:
            pre = str(i[0]).split(",")
            for p in pre:
                if p == DEF_PREFIX:
                    continue
                prefixes.append({"guildId": int(guildId), "prefix": str(p)})

        i = i[2:]
        channels.append(
            {
                "guildId": int(guildId),
                "welcomeCh": i[0],
                "farewellCh": i[0],
                "purgatoryCh": i[2],
                "announcementCh": i[4],
            }
        )

    async with NEW_DB.transaction():
        await NEW_DB.execute_many(dbQuery.insertToGuilds, values=guilds)
        await NEW_DB.execute_many(
            "INSERT INTO prefixes VALUES (:guildId, :prefix)", values=prefixes
        )
        await NEW_DB.execute_many(
            """
            INSERT OR IGNORE INTO guildChannels
            VALUES (
                :guildId,
                :welcomeCh,
                :farewellCh,
                NULL,
                :purgatoryCh,
                :announcementCh
            )
        """,
            values=channels,
        )


async def migrateGuildConfigs():
    """Migrate disabled command and welcome/farewell msg"""
    data = await OLD_DB.fetch_all("SELECT * FROM settings")

    disabled = []
    configs = []
    for i in data:
        guildId = i[0]
        i = i[2:]

        dis = (i[0] or "").split(",")
        mod = (i[-1] or "").split(",")
        pre = dis + mod
        for cmd in pre:
            if str(cmd).startswith("command") or str(cmd) == "":
                continue
            disabled.append({"guildId": guildId, "command": str(cmd)})
        i = i[1:]

        configs.append({"guildId": guildId, "welcomeMsg": i[0], "farewellMsg": i[1]})

    async with NEW_DB.transaction():
        await NEW_DB.execute_many(
            "INSERT INTO disabled VALUES (:guildId, :command)", values=disabled
        )
        await NEW_DB.execute_many(
            "INSERT OR IGNORE INTO guildConfigs VALUES (:guildId, 0, 0, :welcomeMsg, :farewellMsg)",
            values=configs,
        )


async def migrateGuildRoles():
    """Migrate guild's special roles"""
    data = await OLD_DB.fetch_all("SELECT * FROM roles")

    async with NEW_DB.transaction():
        await NEW_DB.execute_many(
            "INSERT OR IGNORE INTO guildRoles VALUES (:guildId, NULL, :mutedRole, :autoRole)",
            values=[
                {
                    "guildId": i[0],
                    "mutedRole": i[2],
                    "autoRole": i[1],
                }
                for i in data
            ],
        )


async def migrateGuildCustomCommands():
    """Migrate custom commands"""
    data = await OLD_DB.fetch_all("SELECT * FROM tags")

    # guildId = i[0]
    # i[1:]
    # lookups.append({"guildId": guildId})
    async with NEW_DB.transaction():
        for i in data:
            addedId = await NEW_DB.execute(
                """
                    INSERT INTO commands (name, content, ownerId, createdAt, type, uses)
                    VALUES (:name, :content, :ownerId, :createdAt, :type, :uses)
                """,
                values={
                    "name": i[1],
                    "content": i[2],
                    "ownerId": i[-1],
                    "createdAt": i[3],
                    "type": "text",
                    "uses": i[5],
                },
            )
            await NEW_DB.execute(
                """
                    INSERT INTO commands_lookup (cmdId, name, guildId)
                    VALUES (:cmdId, :name, :guildId)
                """,
                values={"cmdId": addedId, "name": i[1], "guildId": i[0]},
            )


async def main():
    await OLD_DB.connect()
    await prepareNewDB()
    await migrateGuildData()
    await migrateGuildConfigs()
    await migrateGuildRoles()
    await migrateGuildCustomCommands()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
