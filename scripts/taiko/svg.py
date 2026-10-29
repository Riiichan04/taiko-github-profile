"""Experimental self-contained compact SVG animation; no scripts or raster frames."""
import json
import math
from xml.etree.ElementTree import Element, tostring
from .svg_elements import element, fmt
from .svg_backgrounds import define_backgrounds, draw_background, draw_original_background, draw_festival_background
from .svg_notes import define_note_shapes, create_note
from .drum import ROLL_VISUAL_RATE

NS = 'http://www.w3.org/2000/svg'
WIDTH, HEIGHT, TARGET, CENTER = 766, 108, 171, 54


def pulse(parent, events, duration, hold=.1, attribute='opacity', on='1', off='0'):
    intervals=[]
    for timestamp in events:
        start=timestamp % duration
        end=start+min(hold,duration)
        intervals.append((start,min(end,duration)))
        if end>duration:intervals.append((0,end-duration))
    merged=[]
    for start,end in sorted(intervals):
        if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
        else:merged.append((start,end))
    points={0:off,1:off}
    for start,end in merged:
        points[start/duration]=on
        points[end/duration]=off
    keys=sorted(points)
    parent.set(attribute,points[0])
    if merged:
        attrs = dict(attributeName=attribute,dur=fmt(duration)+'s',repeatCount='indefinite',
                     calcMode='discrete',keyTimes=';'.join(fmt(k) for k in keys))
        if attribute == 'transform':
            attrs['type'] = 'translate'
            attrs['values'] = ';'.join(points[k].removeprefix('translate(').removesuffix(')') for k in keys)
            element(parent,'animateTransform',**attrs)
        else:
            element(parent,'animate',values=';'.join(points[k] for k in keys),**attrs)


def export_svg(chart, output, background='festival', variant='full'):
    if variant not in ('full', 'classic'):
        raise ValueError('SVG variant must be full or classic')
    duration=chart['beats']*60/chart['bpm']
    speed=chart['speed'];distance=duration*speed
    root=Element('svg',{'xmlns':NS,'width':str(WIDTH),'height':str(HEIGHT),
                        'viewBox':f'0 0 {WIDTH} {HEIGHT}','role':'img'})
    element(root,'title').text='Tiny Taiko contribution animation'
    element(root,'desc').text=f'{chart["bpm"]} BPM, {duration:.3f} seconds, same TJA timing as the GIF. Experimental SVG.'
    element(root,'metadata').text=json.dumps({'bpm':chart['bpm'],'duration_seconds':duration,
        'scroll_pixels_per_second':speed,'notes':len(chart['notes']),
        'roll_visual_rate':ROLL_VISUAL_RATE,'format':'vector-only SMIL; no JavaScript'},separators=(',',':'))
    defs=element(root,'defs')
    clip=element(defs,'clipPath',id='panel');element(clip,'rect',width=116,height=108)
    clip=element(defs,'clipPath',id='lane');element(clip,'rect',x=150,y=3,width=616,height=102)
    # The rectangular roll body must never extend left of the hit center.
    # Tap circles and approaching roll heads retain the wider lane clip.
    clip=element(defs,'clipPath',id='roll-body-lane')
    element(clip,'rect',x=TARGET,y=3,width=WIDTH-TARGET,height=102)
    define_backgrounds(defs)
    define_note_shapes(defs)

    panel=draw_background(root,background)
    element(root,'path',d='M116 1.5 H766 M116 106.5 H766 M116 0 V108',fill='none',stroke='#fff3d8',stroke_width=3)
    element(root,'path',d='M117 54 H766',stroke='#504047',stroke_width=1)
    for radius,color,width in ((28,'#fff3d8',3),(20,'#78675f',1)):
        element(root,'circle',cx=TARGET,cy=CENTER,r=radius,fill='none',stroke=color,stroke_width=width)

    beat_seconds=60/chart['bpm']
    feedback={('don','left'):[],('don','right'):[],('ka','left'):[],('ka','right'):[]}
    target_events=[];visual_events=[];parity=0
    notes=sorted(chart['notes'],key=lambda n:n['beat'])
    static=element(defs,'g',id='chart')
    static_bodies=element(defs,'g',id='roll-bodies')
    body_layer=element(root,'g',clip_path='url(#roll-body-lane)')
    moving_bodies=element(body_layer,'g')
    element(moving_bodies,'animateTransform',attributeName='transform',type='translate',
            values=f'0 0;{fmt(-distance)} 0',dur=fmt(duration)+'s',repeatCount='indefinite',calcMode='linear')
    primary=element(root,'g',clip_path='url(#lane)')
    moving=element(primary,'g')
    element(moving,'animateTransform',attributeName='transform',type='translate',
            values=f'0 0;{fmt(-distance)} 0',dur=fmt(duration)+'s',repeatCount='indefinite',calcMode='linear')

    # Primary notes disappear exactly at their hit (or roll end). Future cycles
    # share these static shapes and must cover the lane even just before reset.
    for n in reversed(notes):
        if n['type']=='roll':
            create_note(static_bodies,n,beat_seconds,speed,TARGET,CENTER,roll_part='body')
            body=create_note(moving_bodies,n,beat_seconds,speed,TARGET,CENTER,roll_part='body')
            end=n['end']*beat_seconds
            if end<duration:
                element(body,'animate',attributeName='visibility',values='visible;hidden;hidden',
                        keyTimes=f'0;{fmt(end/duration)};1',dur=fmt(duration)+'s',
                        repeatCount='indefinite',calcMode='discrete')
        create_note(static,n,beat_seconds,speed,TARGET,CENTER,roll_part='head')
        group=create_note(moving,n,beat_seconds,speed,TARGET,CENTER,roll_part='head')
        end=n['beat']*beat_seconds
        if end<=0:group.set('visibility','hidden')
        elif end<duration:
            element(group,'animate',attributeName='visibility',values='visible;hidden;hidden',
                    keyTimes=f'0;{fmt(end/duration)};1',dur=fmt(duration)+'s',
                    repeatCount='indefinite',calcMode='discrete')
    if notes:
        # At the end of a cycle the strip has moved left by one full distance.
        # Include the outer tap radius/stroke so notes enter at the right edge
        # continuously rather than popping in when their centers become visible.
        future_cycles = math.ceil((WIDTH-TARGET+22.5)/distance)+1
        for cycle in range(1, future_cycles+1):
            shift = f'translate({fmt(cycle*distance)} 0)'
            element(moving,'use',href='#chart',transform=shift)
            if len(static_bodies):
                element(moving_bodies,'use',href='#roll-bodies',transform=shift)

    for n in notes:
        start=n['beat']*beat_seconds
        if n['type']=='roll':
            end=n['end']*beat_seconds
            count=n.get('hits',max(1,round((end-start)*16)))
            target_events.extend(start+i*(end-start)/count for i in range(count))
            step=(end-start)/count/ROLL_VISUAL_RATE
            for i in range(math.ceil((end-start)/step)):
                t=start+i*step
                if t<end:
                    feedback[('don','left' if i%2==0 else 'right')].append(t);visual_events.append(t)
            parity+=count
            head=element(root,'circle',cx=TARGET,cy=CENTER,r=20,fill='#ffd866',stroke='#fff3d8',stroke_width=2)
            pulse(head,[start],duration,hold=end-start)
        else:
            hand=n.get('hand','left' if parity%2==0 else 'right')
            feedback[(n['type'],hand)].append(start)
            target_events.append(start);visual_events.append(start);parity+=1
    ring=element(root,'circle',cx=TARGET,cy=CENTER,r=33,fill='none',stroke='#ffd87d',stroke_width=2)
    pulse(ring,target_events,duration,hold=.08)
    drum=element(panel,'g')
    pulse(drum,visual_events,duration,hold=.11,attribute='transform',on='translate(0 -1.5)',off='translate(0 0)')
    element(drum,'ellipse',cx=59,cy=103,rx=37,ry=4,fill='#bf5138')
    element(drum,'circle',cx=59,cy=65.7,r=37.8,fill='#e55b43',stroke='#302a30',stroke_width=2.3)
    element(drum,'path',d='M21.2 48 V65.7 M96.8 48 V65.7',stroke='#302a30',stroke_width=2.3)
    element(drum,'rect',x=22.3,y=48,width=73.4,height=17.7,fill='#e55b43')
    for cy,r,fill,stroke in ((53.4,37.8,'#cbd0dc','#302a30'),(48,37.8,'#faf9f5','#302a30'),(48,31.6,'#e9edf6','#d3d9e5')):
        element(drum,'circle',cx=59,cy=cy,r=r,fill=fill,stroke=stroke,stroke_width=2.3 if r>35 else .8)
    for (kind,hand),events in feedback.items():
        sweep=0 if hand=='left' else 1
        if kind=='don':
            shape=element(drum,'path',d=f'M59 19.5 A28.5 28.5 0 0 {sweep} 59 76.5 Z',fill='#f86150')
        else:
            shape=element(drum,'path',d=f'M59 12.5 A35.5 35.5 0 0 {sweep} 59 83.5',fill='none',stroke='#55c5d6',stroke_width=4.6)
        pulse(shape,events,duration,hold=.11)
    for angle in range(20,170,25):
        a=math.radians(angle)
        element(drum,'circle',cx=fmt(59+35.5*math.cos(a)),cy=fmt(53.4+35.5*math.sin(a)),r='.9',fill='#66595d')
    if variant == 'classic':
        root.set('width', '800'); root.set('height', '220')
        root.set('viewBox', '0 0 800 220')
        visual = [child for child in root if child.tag not in ('defs', 'title', 'desc', 'metadata')]
        for child in visual:
            root.remove(child)
        backdrop = element(root, 'g', transform='scale(6.896551724 2.037037037)')
        (draw_festival_background if background == 'festival' else draw_original_background)(backdrop)
        lane = element(root, 'g', transform='translate(34 65)')
        for child in visual:
            if child is not panel:
                lane.append(child)
        drum_panel = element(root, 'g', transform='translate(0 40) scale(1.293103448)')
        drum_panel.append(panel)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(tostring(root,encoding='utf-8',xml_declaration=True))
    print(f'{output}: {output.stat().st_size/1024:.1f} KiB; {duration:.3f}s; {len(notes)} note objects')
    return root
