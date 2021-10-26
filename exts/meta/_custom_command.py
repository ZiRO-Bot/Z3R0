from core import db
from core.errors import CCommandNotFound

from ._objects import CustomCommand


async def getCustomCommand(ctx, command):  # type: ignore
    """Get custom command from database."""
    lookup = await db.CommandsLookup.filter(name=command, guild_id=ctx.guild.id).first()
    if not lookup:
        # No command found
        raise CCommandNotFound(command)

    _id = lookup.cmd_id  # type: ignore
    name = lookup.name

    results = await db.CommandsLookup.filter(cmd_id=_id).prefetch_related("cmd")
    if not results:
        raise CCommandNotFound(command)

    command: db.Commands = results[0].cmd  # type: ignore

    return CustomCommand(
        id=_id,
        content=command.content,
        name=command.name,
        invokedName=name,
        description=command.description,
        category=command.category,
        aliases=[alias.name for alias in results if alias.name != command.name],
        uses=command.uses,
        url=command.url,
        owner=command.ownerId,
        enabled=command.enabled,
    )


async def getCustomCommands(guildId, category: str = None):
    """Get all custom commands from guild id."""

    # cmds = {
    #     "command_id": {
    #         "name": "command",
    #         "description": null,
    #         "category": null,
    #         "aliases": ["alias", ...]
    #     }
    # }

    cmds = {}

    query = db.CommandsLookup.filter(guild_id=guildId)
    if category:
        query = query.filter(cmd__category=category.lower())

    lookupRes = await query.prefetch_related("cmd")

    if not lookupRes:
        return []

    # Create temporary dict
    for lookup in lookupRes:
        cmd: db.Commands = lookup.cmd  # type: ignore

        isAlias = lookup.name != cmd.name

        if cmd.id not in cmds:
            cmds[cmd.id] = {}

        if not isAlias:
            # If its not an alias
            cmds[cmd.id] = {
                "name": cmd.name,  # "real" name
                "description": cmd.description,
                "category": cmd.category,
                "owner": cmd.ownerId,
                "enabled": cmd.enabled,
                "uses": cmd.uses,
            }
        else:
            try:
                cmds[cmd.id]["aliases"] += [lookup.name]
            except KeyError:
                cmds[cmd.id]["aliases"] = [lookup.name]

    return [CustomCommand(id=k, **v) for k, v in cmds.items()]
