# Just bunch of SQL query
createCommandsTable = """
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER NOT NULL UNIQUE,
        name TEXT,
        content TEXT,
        uses INTEGER DEFAULT 0,
        ownerId INTEGER,
        createdAt REAL,
        PRIMARY KEY("id" AUTOINCREMENT)
    );
"""

createCommandsLookupTable = """
    CREATE TABLE IF NOT EXISTS commands_lookup (
        cmdId INTEGER NOT NULL,
        name TEXT,
        guildId INTEGER,
        FOREIGN KEY("cmdId") REFERENCES commands("id")
    );
"""
