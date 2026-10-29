"""Drawing helpers in logical pixels, supersampled for smooth edges."""
from PIL import ImageDraw
from .config import SCALE

class Canvas:
    def __init__(self, image):
        self.image = image
        self.draw = ImageDraw.Draw(image)

    def box(self, rect, fill, outline=None, width=1, radius=0):
        rect = tuple(round(v*SCALE) for v in rect)
        if radius:
            self.draw.rounded_rectangle(rect, radius=radius*SCALE, fill=fill, outline=outline, width=width*SCALE)
        else:
            self.draw.rectangle(rect, fill=fill, outline=outline, width=width*SCALE)

    def oval(self, rect, fill, outline=None, width=1):
        self.draw.ellipse(tuple(round(v*SCALE) for v in rect), fill=fill, outline=outline, width=width*SCALE)

    def line(self, points, fill, width=1):
        self.draw.line([(round(x*SCALE), round(y*SCALE)) for x, y in points], fill=fill, width=width*SCALE)

