"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from discord.ext import commands


class Group:
    """Dummy class for splitted subcommands group"""

    def __init__(self, command: commands.Group, subcommands: list):
        self.self = command
        self.commands = subcommands
