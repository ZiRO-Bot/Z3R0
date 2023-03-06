"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Optional, Union

import discord
from discord.ext import commands

from ...core.flags import StringAndFlags


class AnnouncementFlags(StringAndFlags, case_insensitive=True):
    target: Union[discord.Role, str] = "everyone"
    channel: Optional[discord.TextChannel] = commands.flag(aliases=("ch",))
