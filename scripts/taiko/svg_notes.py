"""Reusable SVG Don/Ka symbols and timeline-positioned note instances."""
from .svg_elements import element, fmt


def _draw_tap(parent, kind, color):
    group=element(parent,'g',id=kind)
    element(group,'circle',r=21,fill=color,stroke='#442b2d',stroke_width=3)
    element(group,'circle',r=17,fill='none',stroke='#fff3d8',stroke_width=2)
    return group


def draw_don(parent):
    """Define the red Don symbol; geometry is shared with Ka."""
    return _draw_tap(parent,'don','#f86150')


def draw_ka(parent):
    """Define the blue Ka symbol; geometry is shared with Don."""
    return _draw_tap(parent,'ka','#55c5d6')


def define_note_shapes(defs):
    draw_don(defs)
    draw_ka(defs)


def create_note(parent,n,beat_seconds,speed,target=171,center=54,roll_part='all'):
    start=n['beat']*beat_seconds;x=target+start*speed
    if n['type']=='roll':
        length=(n['end']-n['beat'])*beat_seconds*speed
        group=element(parent,'g',transform=f'translate({fmt(x)} {center})')
        if roll_part in ('all','body'):
            element(group,'rect',y=-18,width=fmt(length),height=36,rx=16,fill='#f5c64d',stroke='#442b2d',stroke_width=2)
        if roll_part in ('all','head'):
            element(group,'circle',r=20,fill='#ffd866',stroke='#442b2d',stroke_width=3)
            element(group,'circle',r=15,fill='none',stroke='#fff3d8',stroke_width=2)
    else:
        group=element(parent,'use',href='#'+n['type'],x=fmt(x),y=center)
    return group

