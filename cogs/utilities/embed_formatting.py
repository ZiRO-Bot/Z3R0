import discord

def error(text: str):
    return f"⛔ {text}"

def success(text: str):
    return f"✅ {text}"

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
    
