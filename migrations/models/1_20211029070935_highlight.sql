-- upgrade --
CREATE TABLE IF NOT EXISTS "highlight" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "text" TEXT NOT NULL,
    "ownerId" BIGINT NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guilds" ("id") ON DELETE CASCADE
);
-- downgrade --
DROP TABLE IF EXISTS "highlight";
