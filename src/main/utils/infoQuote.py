"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""


def info(
    message: str,
    *,
    title: str = "Information",
    emoji: str = "<:info:783206485051441192>",
    indent: int = 4,
    codeBlock: bool = False
):
    messages = message.split("\n")
    message = "" if not codeBlock else "> ```diff\n"
    for msg in messages:
        if not codeBlock:
            message += ">{}{}\n".format(" " * indent if indent else "", msg)
        else:
            message += "> {}\n".format(msg)
    message += "" if not codeBlock else "> ```"
    return "> {} **`{}`** \n{}".format(emoji, title, message)
