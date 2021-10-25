# Raw SQL -> ORM

import asyncio
import datetime as dt
import sqlite3

from tortoise import Tortoise

import config
from core import db


OLD = sqlite3.connect("./data/database3_0.db", isolation_level=None)
OLD.execute("pragma journal_mode=wal")
OLD.execute("pragma foreign_keys=ON")
OLD.row_factory = sqlite3.Row


async def main():
    # Init Tortoise
    await Tortoise.init(
        config=config.TORTOISE_ORM,
        use_tz=True,  # d.py now tz-aware
    )
    await Tortoise.generate_schemas(safe=True)

    # Guild list
    guilds = []
    for guild in OLD.execute("SELECT * FROM guilds"):
        guilds.append(db.Guilds(id=guild["id"]))
    # Try to insert guild list into new database
    try:
        await db.Guilds.bulk_create(guilds)
    except Exception:
        # Assume its already migrated
        print("Already migrated")
        await Tortoise.close_connections()
        return

    # Commands + Command Lookups
    for command in OLD.execute("SELECT * FROM commands"):
        await db.Commands.create(
            id=command["id"],
            type=command["type"],
            name=command["name"],
            category=command["category"],
            description=command["description"],
            content=command["content"],
            url=command["url"],
            uses=command["uses"],
            ownerId=command["ownerId"],
            createdAt=dt.datetime.fromtimestamp(
                command["createdAt"], tz=dt.timezone.utc
            ),
            visibility=command["visibility"],
            enabled=command["enabled"],
        )

    for lookup in OLD.execute("SELECT * FROM commands_lookup"):
        try:
            await db.CommandsLookup.create(
                cmd_id=lookup["cmdId"],
                name=lookup["name"],
                guild_id=lookup["guildId"],
            )
        except Exception:
            await db.Commands.filter(id=lookup["cmdId"]).delete()

    prefixes = []
    for prefix in OLD.execute("SELECT * FROM prefixes"):
        prefixes.append(
            db.Prefixes(prefix=prefix["prefix"], guild_id=prefix["guildId"])
        )
    await db.Prefixes.bulk_create(prefixes)

    timers = []
    for timer in OLD.execute("SELECT * FROM timer"):
        timers.append(
            db.Timer(
                id=timer["id"],
                event=timer["event"],
                extra=timer["extra"],
                expires=dt.datetime.fromtimestamp(timer["expires"], tz=dt.timezone.utc),
                created=dt.datetime.fromtimestamp(timer["created"], tz=dt.timezone.utc),
                owner=timer["owner"],
            )
        )
    await db.Timer.bulk_create(timers)

    caseLogs = []
    for log in OLD.execute("SELECT * FROM caseLog"):
        caseLogs.append(
            db.CaseLog(
                caseId=log["caseId"],
                type=log["type"],
                modId=log["modId"],
                targetId=log["targetId"],
                reason=log["reason"],
                createdAt=dt.datetime.fromtimestamp(
                    log["createdAt"], tz=dt.timezone.utc
                ),
                guild_id=log["guildId"],
            )
        )
    await db.CaseLog.bulk_create(caseLogs)

    disabledCmds = []
    for cmd in OLD.execute("SELECT * FROM disabled"):
        disabledCmds.append(
            db.Disabled(
                command=cmd["command"],
                guild_id=cmd["guildId"],
            )
        )
    await db.Disabled.bulk_create(disabledCmds)

    channels = []
    for channel in OLD.execute("SELECT * FROM guildChannels"):
        channels.append(
            db.GuildChannels(
                guild_id=channel["guildId"],
                welcomeCh=channel["welcomeCh"],
                farewellCh=channel["farewellCh"],
                modlogCh=channel["modlogCh"],
                purgatoryCh=channel["purgatoryCh"],
                announcementCh=channel["announcementCh"],
            )
        )
    await db.GuildChannels.bulk_create(channels)

    configs = []
    for c in OLD.execute("SELECT * FROM guildConfigs"):
        configs.append(
            db.GuildConfigs(
                ccMode=c["ccMode"],
                tagMode=c["tagMode"],
                welcomeMsg=c["welcomeMsg"],
                farewellMsg=c["farewellMsg"],
                guild_id=c["guildId"],
            )
        )
    await db.GuildConfigs.bulk_create(configs)

    mutes = []
    for mute in OLD.execute("SELECT * FROM guildMutes"):
        mutes.append(
            db.GuildMutes(
                mutedId=mute["mutedId"],
                guild_id=mute["guildId"],
            )
        )
    await db.GuildMutes.bulk_create(mutes)

    roles = []
    for role in OLD.execute("SELECT * FROM guildRoles"):
        roles.append(
            db.GuildRoles(
                modRole=role["modRole"],
                mutedRole=role["mutedRole"],
                autoRole=role["autoRole"],
                guild_id=role["guildId"],
            )
        )
    await db.GuildRoles.bulk_create(roles)

    # Migration complete
    print("DONE")
    await Tortoise.close_connections()
    return


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
