from discord.ext import ipc
from quart import Quart


app = Quart(__name__)
ipc_client = ipc.Client(
    secret_key="helloworld"
)  # secret_key must be the same as your server


@app.route("/")
async def index():
    guild = await ipc_client.request(
        "get_guild", guild_id=807260318270619748
    )  # get the member count of server with ID 12345678

    return str(guild)  # display member count


if __name__ == "__main__":
    app.run()
