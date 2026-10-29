"""Original and festival backgrounds; cache the static festival art."""
import math
from .config import WIDTH, HEIGHT, SCALE, INK

FESTIVAL_BACKGROUND = None
ORIGINAL_BACKGROUND = None

def draw_background(canvas, festival=False):
    global FESTIVAL_BACKGROUND, ORIGINAL_BACKGROUND
    image, d = canvas.image, canvas.draw
    box, oval, line = canvas.box, canvas.oval, canvas.line
    cached = FESTIVAL_BACKGROUND if festival else ORIGINAL_BACKGROUND
    if cached is not None:
        image.paste(cached)
        return
    # Quiet geometric backdrop and a single high-contrast note highway.
    box((0, 0, WIDTH, 9), INK)
    box((0, 204, WIDTH, HEIGHT), INK)
    for x in range(-100, WIDTH+100, 95):
        line([(x, 9), (x+110, 204)], '#ed7c4d', 22)
    if festival and FESTIVAL_BACKGROUND is not None:
        image.paste(FESTIVAL_BACKGROUND)
    elif festival:
        # Original procedural backdrop: warm radial glow, sunburst, wave bands.
        for y in range(HEIGHT):
            for x in range(0, WIDTH, 4):
                glow = max(0, 1-math.hypot((x-65)/560, (y-95)/260))
                color = (int(48+96*glow), int(19+27*glow), int(38+12*glow))
                box((x, y, x+4, y+1), color)
        for angle in range(-110, 120, 22):
            a, b = math.radians(angle), math.radians(angle+7)
            points = [(77,119),(77+1000*math.cos(a),119+1000*math.sin(a)),
                      (77+1000*math.cos(b),119+1000*math.sin(b))]
            d.polygon([(round(x*SCALE),round(y*SCALE)) for x,y in points], fill='#813736')
        for row in range(3):
            for x in range(-40, WIDTH+60, 60):
                for radius in (16, 23, 30):
                    cx, cy = x+(30 if row%2 else 0), 222-row*16
                    d.arc(((cx-radius)*SCALE,(cy-radius)*SCALE,(cx+radius)*SCALE,(cy+radius)*SCALE),
                          180,360,fill='#a85c48',width=SCALE)
        for x,y in ((24,27),(119,28),(297,19),(486,43),(659,17),(749,49),(133,188)):
            line([(x-3,y),(x+3,y)], '#edc58d', 1)
            line([(x,y-3),(x,y+3)], '#edc58d', 1)
        box((0,0,WIDTH,3),'#e7b77e')
        box((0,217,WIDTH,HEIGHT),'#e7b77e')
        oval((9,48,145,184),None,'#b96d4a',1)
        oval((16,55,138,177),None,'#e2aa70',1)
        FESTIVAL_BACKGROUND = image.copy()

    if not festival:
        ORIGINAL_BACKGROUND = image.copy()
