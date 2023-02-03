"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import List, Union

import discord


class LinkView(discord.ui.View):
    def __init__(self, *, links: List[Union[str, tuple]]) -> None:
        super().__init__()
        for link in links:
            if isinstance(link, tuple):
                label, link = link
            else:
                label = link

            self.add_item(discord.ui.Button(label=label, url=link))
