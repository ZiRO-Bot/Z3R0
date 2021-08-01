# My attempt on using SQLAlchemy to support multiple SQL Languages

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
)


metadata = MetaData()

commands = Table(
    "commands",
    metadata,
    Column(
        "id",
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        unique=True,
    ),
    Column("type", String),
    Column("name", String),
    Column("category", String, default="unsorted"),
    Column("description", String),
    Column("content", String),
    Column("url", String),
    Column("uses", Integer, default=0),
    Column("ownerId", BigInteger().with_variant(Integer, "sqlite")),
    Column("createdAt", Float),
    Column("visibility", Integer, default=0),
    Column("enabled", Integer, default=1),
    sqlite_autoincrement=True,  # Allow sqlite to auto increment
)

commandsLookup = Table(
    "commands_lookup",
    metadata,
    Column(
        "cmdId",
        ForeignKey("commands.id"),
    ),
    Column("name", String),
    Column("guildId", ForeignKey("guilds.id")),
)

guilds = Table(
    "guilds",
    metadata,
    Column(
        "id",
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        unique=True,
    ),
)

if __name__ == "__main__":
    # print(commandsLookup.create)
    print(commands.update(commands.c.id == 5).values(category="test"))
