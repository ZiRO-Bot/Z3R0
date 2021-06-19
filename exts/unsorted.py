"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import discord


from core.mixin import CogMixin
from discord.ext import commands


class Admin(commands.Cog, CogMixin):
    """Admin-only commands to configure the bot."""

    icon = "\u2699"
    cc = True


def setup(bot):
    bot.add_cog(Admin(bot))
