import os
import discord
import json
import aiohttp
import logging

from discord.ext import commands

token = os.getenv('TOKEN') or None
shard = os.getenv('SHARD') or 0
shard_count = os.getenv('SHARD_COUNT') or 1

extensions = [
	"cogs.welcome", "cogs.help", "cogs.moderator", 
    "cogs.general", "cogs.utils", "cogs.mcbe",
    "cogs.anilist"
]

# def check_jsons():
#     try:
#         f = open('config.json', 'r')
#     except FileNotFoundError:
#         token = input('Enter your bot\'s token: ')
#         with open('config.json', 'w+') as f:
#             json.dump({"token": token}, f, indent=4)

def get_prefix(bot, message):
	"""A callable Prefix for our bot. This could be edited to allow per server prefixes."""

	prefixes = ['>', '$>', '.']

	# Check to see if we are outside of a guild. e.g DM's etc.
	# if not message.guild:
	# Only allow ? to be used in DMs
	#   return '?'

	# If we are in a guild, we allow for the user to mention us or use any of the prefixes in our list.
	return commands.when_mentioned_or(*prefixes)(bot, message)

class ziBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = logging.getLogger('discord')
        self.session = aiohttp.ClientSession()
        
        # check_jsons()

        # with open('config.json', 'r') as f:
        #     self.config = json.load(f)
        #     config = self.config

        with open('custom_commands.json', 'r') as cc:
            self.custom_commands = json.load(cc)
        
        # Remove help command (for custom help command)
        self.remove_command('help')

    async def on_ready(self): 
        activity=discord.Activity(name="over your shoulder",type=discord.ActivityType.watching)
        await self.change_presence(activity=activity)

        for extension in extensions:
            self.load_extension(extension)
        
        self.logger.warning(f'Online: {self.user} (ID: {self.user.id})')

    async def on_message(self, message):
        await self.process_commands(message)

        try:
            command = message.content.split()[0]
        except IndexError:
            pass
        
        try:
            if command in self.custom_commands:
                await message.channel.send(self.custom_commands[command])
                return
        except:
            return
        
        self.logger.warning(f' \nMessage from {message.author}: {message.content} \n on {message.channel}')

    def run(self):
        super().run(token, reconnect=True)
