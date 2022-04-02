from io import BytesIO
from random import randint
from typing import List

from PIL import Image, UnidentifiedImageError

from ..core.decorators import in_executor


def bytes2image(image: bytes) -> Image.Image:
    if image.__sizeof__() > 10 * (2**20):
        raise ValueError("Exceeds 10MB")
    try:
        io: BytesIO = BytesIO(image)
        io.seek(0)
        return Image.open(io)
    except UnidentifiedImageError:
        raise ValueError("Unable to use Image")


def image2bytes(image: Image.Image, format: str = "PNG") -> BytesIO:
    byteArray = BytesIO()
    image.save(byteArray, format=format)  # type: ignore
    byteArray.seek(0)
    return byteArray


@in_executor()
def rectangle(R: int, G: int, B: int) -> BytesIO:
    img = Image.new("RGB", (500, 500), (R, G, B))
    return image2bytes(img)


# Stuff below will be replaced by ImageManip repo (which can be hosted using
# heroku or glitch or repl.it)
# https://github.com/ZiRO-Bot/ImageManip


@in_executor()
def blurplify(imgByte: bytes) -> BytesIO:
    img = bytes2image(imgByte)
    im = img.resize((400, 400), 1)
    w, h = im.size
    blurple = Image.new("RGBA", (w, h), color=(88, 101, 242, 160))
    im.paste(blurple, mask=blurple)
    return image2bytes(im)


@in_executor()
def triggered(imgByte: bytes) -> BytesIO:
    img = bytes2image(imgByte)
    img = img.resize((500, 500), 1)
    frames: List[Image.Image] = []
    for frame in range(30):
        canvas = Image.new("RGBA", (400, 400))
        x = -1 * (randint(50, 100))
        y = -1 * (randint(50, 100))
        canvas.paste(img, (x, y))
        red = Image.new("RGBA", (400, 400), color=(255, 0, 0, 80))
        canvas.paste(red, mask=red)
        frames.append(canvas)
    byteArray = BytesIO()
    frames[0].save(byteArray, format="GIF", save_all=True, loop=0, append_images=frames)
    byteArray.seek(0)
    return byteArray
