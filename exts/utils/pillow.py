import io


from core.decorators import in_executor
from PIL import Image


@in_executor()
def rectangle(R, G, B):
    img = Image.new('RGB', (500, 500), (R, G, B))
    byteArray = io.BytesIO()
    img.save(byteArray, format="PNG")
    byteArray.seek(0)
    return byteArray
