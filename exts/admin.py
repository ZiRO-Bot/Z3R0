"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import discord


from discord.ext import commands


class Admin(commands.Cog):
    """Admin-only commands to configure the bot."""
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(Admin(bot))
