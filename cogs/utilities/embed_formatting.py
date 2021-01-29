import discord

def error(text: str):
    return f"<:error:783265883228340245> {text}"

def success(text: str):
    return f"✅ {text}"

def embedError(_error):
    embed = discord.Embed(
            title = "Error!", description=error(_error), colour=discord.Colour(0x2F3136)
        )
    return embed

def embedDefault(context = None, **kwargs):
    if not context:
        return discord.Embed(**kwargs)
    kwargs.pop("timestamp", None)
    embed = discord.Embed(timestamp=context.message.created_at, **kwargs)
    embed.set_footer(
        text=f"Requested by {context.author}",
        icon_url=context.author.avatar_url,
    )
    return embed

async def em_ctx_send_error(ctx, text):
    embed = discord.Embed(
            title = "Error!", description=error(text), colour=discord.Colour(0x2F3136)
        )
    await ctx.send(embed=embed)

async def em_ctx_send_success(ctx, text):
    embed = discord.Embed(
            title = "Success!", description=success(text), colour=discord.Colour(0x2F3136)
        )
    await ctx.send(embed=embed)
    
