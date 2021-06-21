"""Just bunch of SQL query."""

createTimerTable = """
    CREATE TABLE IF NOT EXISTS timer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT,
        extra TEXT,
        expires REAL,
        created REAL,
        owner INT
    )
"""

createCommandsTable = """
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        name TEXT,
        category TEXT DEFAULT "unsorted",
        description TEXT,
        content TEXT,
        url TEXT,
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
    INSERT INTO commands (name, content, ownerId, createdAt, type, url)
    VALUES (:name, :content, :ownerId, :createdAt, :type, :url)
"""

updateCommandUrl = """
    UPDATE commands
    SET url=:url
    WHERE commands.id=:id
"""

deleteCommand = """
    DELETE FROM commands
    WHERE id=:id
"""

insertToCommandsLookup = """
    INSERT INTO commands_lookup (cmdId, name, guildId)
    VALUES (:cmdId, :name, :guildId)
"""

deleteCommandAlias = """
    DELETE FROM commands_lookup
    WHERE (name=:name AND guildId=:guildId)
"""

getCommandId = """
    SELECT cmdId, name FROM commands_lookup
    WHERE (name=:name AND guildId=:guildId)
"""

getCommandContent = """
    SELECT
        commands.content,
        commands.name,
        commands_lookup.name,
        commands.description,
        commands.category,
        commands.uses,
        commands.url,
        commands.ownerId,
        commands.enabled
    FROM commands
    JOIN commands_lookup
        ON commands_lookup.cmdId=commands.id
    WHERE commands.id=:id
"""

updateCommandContent = """
    UPDATE commands
    SET content=:content
    WHERE commands.id=:id
"""

getCommands = """
    SELECT
        commands.id,
        commands_lookup.name,
        commands.name,
        commands.description,
        commands.category,
        commands.ownerId,
        commands.enabled
    FROM commands_lookup
    JOIN commands
        ON commands.id = commands_lookup.cmdId
    WHERE
        commands_lookup.guildId = :guildId
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

createDisabledTable = """
    CREATE TABLE IF NOT EXISTS disabled (
        guildId INTEGER NOT NULL,
        command TEXT,
        FOREIGN KEY ("guildId") REFERENCES guilds ("id") ON DELETE CASCADE
    )
"""

createPrefixesTable = """
    CREATE TABLE IF NOT EXISTS prefixes (
        guildId INTEGER NOT NULL,
        prefix TEXT,
        FOREIGN KEY ("guildId") REFERENCES guilds ("id") ON DELETE CASCADE
    )
"""

createGuildConfigsTable = """
    CREATE TABLE IF NOT EXISTS guildConfigs (
        guildId INTEGER PRIMARY KEY,
        ccMode INTEGER DEFAULT 0,
        tagMode INTEGER DEFAULT 0,
        welcomeMsg TEXT,
        farewellMsg TEXT,
        FOREIGN KEY ("guildId") REFERENCES guilds ("id") ON DELETE CASCADE
    )
"""

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
