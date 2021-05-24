"""Just bunch of SQL query."""

createCommandsTable = """
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        type TEXT,
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
