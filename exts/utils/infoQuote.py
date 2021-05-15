def info(message: str, *, title: str="Information"):
    messages = message.split("\n")
    message = ""
    for msg in messages:
        message += ">     {}\n".format(msg)
    return "> <:info:783206485051441192> **`{}`** \n{}".format(title, message)
