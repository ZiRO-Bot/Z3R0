from core.decorators import in_executor
from io import BytesIO
from PIL import Image, UnidentifiedImageError


def bytes2image(image: bytes) -> Image:
    if image.__sizeof__() > 10 * (2 ** 20):
        raise ValueError("Exceeds 10MB")
    try:
        io = BytesIO(image)
        io.seek(0)
        return Image.open(io)
    except UnidentifiedImageError:
        raise ValueError("Unable to use Image")

def image2bytes(image: Image, format: str = "PNG") -> bytes:
    byteArray = BytesIO()
    image.save(byteArray, format=format)
    byteArray.seek(0)
    return byteArray


@in_executor()
def rectangle(R, G, B):
    img = Image.new('RGB', (500, 500), (R, G, B))
    return image2bytes(img)

@in_executor()
def blurplify(imgByte):
    img = bytes2image(imgByte)
    im = img.resize((400, 400), 1)
    w, h = im.size
    blurple = Image.new("RGBA", (w, h), color=(88, 101, 242, 160))
    im.paste(blurple, mask=blurple)
    return image2bytes(im)
