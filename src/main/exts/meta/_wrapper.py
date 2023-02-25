"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from discord.ext import commands


class GroupSplitWrapper:
    """Wrapper class to split group's subcommands"""

    def __init__(self, command: commands.Group, subcommands: list):
        self.origin = command
        self.commands = subcommands
