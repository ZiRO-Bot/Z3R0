"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from discord.enums import Enum


class Emojis(Enum):
    ok = "<:ok2_0:873464878982115360>"
    error = "<:error:783265883228340245>"
    loading = "<a:loading:776255339716673566>"
    first = "<:first:873473059837870131>"
    back = "<:back:873473128175636480>"
    next = "<:next:873471591642726400>"
    last = "<:last:873471805120208926>"
    stop = "<:stop:873474135941066762>"
    info = "<:info:783206485051441192>"

    def __str__(self) -> str:
        return self.value
