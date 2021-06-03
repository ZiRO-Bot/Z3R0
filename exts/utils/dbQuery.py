"""Just bunch of SQL query."""

createCommandsTable = """
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        description TEXT,
        content TEXT,
        uses INTEGER DEFAULT 0,
        ownerId INTEGER,
        createdAt REAL,
        visibility INTEGER DEFAULT 0,
        enabled INTEGER DEFAULT 1
    );
"""

createCommandsLookupTable = """
    CREATE TABLE IF NOT EXISTS commands_lookup (
        cmdId INTEGER NOT NULL,
        name TEXT,
        guildId INTEGER,
        FOREIGN KEY ("cmdId") REFERENCES commands ("id") ON DELETE CASCADE,
        FOREIGN KEY ("guildId") REFERENCES guilds ("id") ON DELETE CASCADE
    );
"""

insertToCommands = """
    INSERT INTO commands (name, content, ownerId, createdAt)
    VALUES (:name, :content, :ownerId, :createdAt)
"""

insertToCommandsLookup = """
    INSERT INTO commands_lookup (cmdId, name, guildId)
    VALUES (:cmdId, :name, :guildId)
"""

getCommandId = """
    SELECT cmdId, name FROM commands_lookup
    WHERE (commands_lookup.name=:name AND commands_lookup.guildId=:guildId)
"""

getCommandContent = """
    SELECT 
        commands.content,
        commands.name,
        commands_lookup.name,
        commands.description,
        commands.category
    FROM commands
    JOIN commands_lookup
        ON commands_lookup.cmdId=commands.id
    WHERE commands.id=:id
"""

getCommands = """
    SELECT 
        commands.id,
        commands_lookup.name,
        commands.name,
        commands.description,
        commands.category
    FROM commands_lookup
    JOIN commands
        ON commands.id = commands_lookup.cmdId
    WHERE commands_lookup.guildId=:guildId
"""

incrCommandUsage = """
    UPDATE commands SET uses = uses + 1
    WHERE commands.id=:id
"""

createGuildsTable = """
    CREATE TABLE IF NOT EXISTS guilds (
        id INTEGER NOT NULL PRIMARY KEY UNIQUE
    )
"""

insertToGuilds = "INSERT OR IGNORE INTO guilds (id) VALUES (:id)"

# --- Alpha feature, not pushed to git yet (Still debating if i should add it or not).
createYTChannelTable = """
    CREATE TABLE IF NOT EXISTS yt_channels (
        channelId TEXT PRIMARY KEY,
        expiredAt INTEGER
    )
"""

createYTSentVideoTable = """
    CREATE TABLE IF NOT EXISTS yt_sent (
        videoId TEXT PRIMARY KEY
    )
"""

createYTGuildSubsTable = """
    CREATE TABLE IF NOT EXISTS yt_subs (
        guildId INTEGER NOT NULL,
        channelId TEXT,
        FOREIGN KEY ("channelId") REFERENCES yt_channels ("channelId") ON DELETE CASCADE
    )
"""
# ---
