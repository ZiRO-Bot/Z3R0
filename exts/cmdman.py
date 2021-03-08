import aiosqlite
import discord

from discord.ext import commands

class CommandManager(commands.Cog):
    def __init__(self, bot):
        """Manage commands (both built-in and user-made), also handle user-made commands"""
        self.bot = bot
        self.db = self.bot.db

        self.bot.loop.create_task(self.asyncInit())

    async def asyncInit(self):
        # commands database table
        await self.db.execute(
            """
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
        )
        await self.db.commit()

        # commands_lookup database table
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS commands_lookup (
                cmdId INTEGER NOT NULL,
                name TEXT,
                guildId INTEGER,
                FOREIGN KEY("cmdId") REFERENCES commands("id")
            );
            """
        )
        await self.db.commit()
    
def setup(bot):
    bot.add_cog(CommandManager(bot))
