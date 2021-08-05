import sqlalchemy as sa

from core.errors import CCommandNotFound
from core.objects import CustomCommand
from utils import dbQuery, sql


async def getCustomCommand(ctx, command):
    """Get custom command from database."""
    db = ctx.db
    try:
        # Build query using SQLAlchemy
        saQuery = (
            sa.select([sql.commandsLookup.c.cmdId, sql.commandsLookup.c.name])
            .where(sql.commandsLookup.c.name == command)
            .where(sql.commandsLookup.c.guildId == ctx.guild.id)
        )
        _id, name = await db.fetch_one(saQuery)
    except TypeError:
        # No command found
        raise CCommandNotFound(command)

    # Build query using SQLAlchemy
    saQuery = (
        sa.select(
            [
                sql.commands.c.content,
                sql.commands.c.name,
                sql.commandsLookup.c.name,
                sql.commands.c.description,
                sql.commands.c.category,
                sql.commands.c.uses,
                sql.commands.c.url,
                sql.commands.c.ownerId,
                sql.commands.c.enabled,
            ]
        )
        .select_from(sql.commands.join(sql.commandsLookup))
        .where(sql.commands.c.id == _id)
    )
    result = await db.fetch_all(saQuery)
    firstRes = result[0]
    return CustomCommand(
        id=_id,
        content=firstRes[0],
        name=firstRes[1],
        invokedName=name,
        description=firstRes[3],
        category=firstRes[4],
        aliases=[row[2] for row in result if row[2] != row[1]],
        uses=firstRes[5] + 1,
        url=firstRes[6],
        owner=firstRes[7],
        enabled=firstRes[8],
    )


async def getCustomCommands(db, guildId, category: str = None):
    """Get all custom commands from guild id."""

    # cmd = {
    #     "command_id": {
    #         "name": "command",
    #         "description": null,
    #         "category": null,
    #         "aliases": ["alias", ...]
    #     }
    # }

    cmds = {}

    query = dbQuery.getCommands
    values = {"guildId": guildId}
    if category:
        query += " AND commands.category = :category"
        values["category"] = category.lower()
    rows = await db.fetch_all(query, values=values)

    # Create temporary dict
    for row in rows:
        isAlias = row[1] != row[2]

        if row[0] not in cmds:
            cmds[row[0]] = {}

        if not isAlias:
            # If its not an alias
            cmds[row[0]] = {
                "name": row[2],  # "real" name
                "description": row[3],
                "category": row[4],
                "owner": row[5],
                "enabled": row[6],
                "uses": row[7],
            }
        else:
            try:
                cmds[row[0]]["aliases"] += [row[1]]
            except KeyError:
                cmds[row[0]]["aliases"] = [row[1]]

    return [CustomCommand(id=k, **v) for k, v in cmds.items()]
