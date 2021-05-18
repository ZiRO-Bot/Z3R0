def info(message: str, *, title: str="Information", emoji: str="<:info:783206485051441192>"):
    messages = message.split("\n")
    message = ""
    for msg in messages:
        message += ">     {}\n".format(msg)
    return "> {} **`{}`** \n{}".format(emoji, title, message)
