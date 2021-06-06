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
