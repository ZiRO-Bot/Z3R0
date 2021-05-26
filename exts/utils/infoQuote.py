def info(
    message: str,
    *,
    title: str = "Information",
    emoji: str = "<:info:783206485051441192>",
    indent: int = 4
):
    messages = message.split("\n")
    message = ""
    for msg in messages:
        print(msg)
        message += ">{}{}\n".format(" " * indent if indent else "", msg)
    return "> {} **`{}`** \n{}".format(emoji, title, message)
