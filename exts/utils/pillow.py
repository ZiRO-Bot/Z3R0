import io

from PIL import Image

async def rectangle(loop, R, G, B):
    def generate():
        img = Image.new('RGB', (500, 500), (R, G, B))
        byteArray = io.BytesIO()
        img.save(byteArray, format="PNG")
        byteArray.seek(0)
        return byteArray
    return await loop.run_in_executor(None, generate)
