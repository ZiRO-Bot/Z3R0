def info(message: str):
    messages = message.split("\n")
    message = ""
    for msg in messages:
        message += ">     {}\n".format(msg)
    return "> <:info:783206485051441192> **`Information`** \n{}".format(message)
