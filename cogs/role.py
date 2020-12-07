import discord

from discord.ext import commands

class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop.create_task(self.async_init())

    async def async_init(self):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Table for reaction role
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS 
                    reaction_roles (
                        guild_id BIGINT REFERENCES guilds(id) ON DELETE CASCADE NOT NULL,
                        message_id BIGINT NOT NULL,
                        emoji TEXT NOT NULL,
                        role BIGINT NOT NULL,
                        one_time BOOL NOT NULL
                    )
                    """
                )


def setup(bot):
    bot.add_cog(ReactionRole(bot))
