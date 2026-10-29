"""SVG background components: original orange stripes and festival artwork."""
import math
from .svg_elements import element, fmt


def define_backgrounds(defs):
    gradient=element(defs,'radialGradient',id='glow',cx='.3',cy='.4',r='.95')
    element(gradient,'stop',offset=0,stop_color='#903b37');element(gradient,'stop',offset=1,stop_color='#301326')
    waves=element(defs,'pattern',id='waves',width=48,height=14,patternUnits='userSpaceOnUse')
    for r in (12,18,24):element(waves,'path',d=f'M{24-r} 14 A{r} {r} 0 0 1 {24+r} 14',fill='none',stroke='#a85c48',stroke_width='.8')


def draw_original_background(panel):
    element(panel,'rect',width=116,height=108,fill='#e66a42')
    for x in range(-100,200,60):element(panel,'path',d=f'M{x} -30 l100 170',stroke='#ed7c4d',stroke_width=17)


def draw_festival_background(panel):
    element(panel,'rect',width=116,height=108,fill='url(#glow)')
    for angle in range(-110,120,22):
        a,b=math.radians(angle),math.radians(angle+7)
        points=f'59,60 {fmt(59+260*math.cos(a))},{fmt(60+260*math.sin(a))} {fmt(59+260*math.cos(b))},{fmt(60+260*math.sin(b))}'
        element(panel,'polygon',points=points,fill='#813736')
    element(panel,'rect',y=80,width=116,height=28,fill='url(#waves)')
    for r in (47,52):element(panel,'circle',cx=59,cy=57,r=r,fill='none',stroke='#c48b5c',stroke_width='.7')


def draw_background(root, background='festival'):
    """Create the lane backdrop and return the panel that also contains the drum."""
    element(root,'rect',width=766,height=108,fill='#302b32')
    panel=element(root,'g',clip_path='url(#panel)')
    if background=='festival':
        draw_festival_background(panel)
    elif background=='original':
        draw_original_background(panel)
    else:
        raise ValueError('SVG background must be original or festival')
    return panel
