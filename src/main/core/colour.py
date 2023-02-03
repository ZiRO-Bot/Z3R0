"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from discord import Colour


class ZColour(Colour):
    @classmethod
    def rounded(cls):
        return cls(0x2F3136)

    @classmethod
    def me(cls):
        return cls(0x3DB4FF)
