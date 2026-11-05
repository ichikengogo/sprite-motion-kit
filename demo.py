"""Original geometric demo, generated locally; no third-party artwork."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
from motion import SIZE,PARTS

def demo(view):
    parts={};layers={}; side=view=='side'
    def piece(name,start,end,width,color,shape=None):
        im=Image.new('RGBA',SIZE);d=ImageDraw.Draw(im)
        if shape: d.polygon(shape,fill=color)
        else:
            d.line([tuple(start),tuple(end)],fill=color,width=width)
            for x,y in (start,end): d.ellipse((x-width/2,y-width/2,x+width/2,y+width/2),fill=color)
        box=im.getbbox();x0,y0,x1,y1=box
        parts[name]={'start':start,'end':end,'polygon':[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],'confirmed':True}
        layers[name]=im
        return d
    piece('torso',[192,210],[192,145],45,'#267e9b',[(172,139),(212,139),(215,215),(169,215)])
    d=piece('head',[192,137],[192,100],51,'#ffd19a');
    if view!='back':
        eyes=[(205,106)] if side else [(182,106),(202,106)]
        for x,y in eyes:d.ellipse((x-3,y-3,x+3,y+3),fill='#142c39')
        d.line([(195 if side else 185,121),(207 if side else 200,121)],fill='#974e35',width=3)
    else:d.arc((176,85,208,113),0,180,fill='#a05a36',width=4)
    for i,s in enumerate(('left','right')):
        offset=(-10 if i==0 else 10) if side else (-16 if i==0 else 16)
        h=[192+offset,212];k=[h[0]+(32 if side else (-27 if i==0 else 27)),266];a=[h[0],324]
        col='#426584' if i==0 else '#6397ba'
        piece(s+'_thigh',h,k,19,col);piece(s+'_shin',k,a,17,col)
        piece(s+'_foot',a,[a[0]+17,324],13,'#192e43')
        sh=[192+(-18 if i==0 else 18),151];el=[sh[0]+(-7 if i==0 else 7),190];wr=[el[0],224]
        piece(s+'_upper_arm',sh,el,15,'#d7a875' if i==0 else '#ffd19a')
        piece(s+'_forearm',el,wr,13,'#d7a875' if i==0 else '#ffd19a')
    order=['left_upper_arm','left_forearm','left_thigh','left_shin','left_foot','right_thigh','right_shin','right_foot','torso','head','right_upper_arm','right_forearm']
    rig={'view':view,'root':[192,210],'parts':parts,'order':order,'origin':'original geometric demo','confirmed':True}
    image=Image.new('RGBA',SIZE)
    for name in order:image.alpha_composite(layers[name])
    return image,rig,layers

if __name__=='__main__':
    dest=Path(__file__).parent/'examples';dest.mkdir(exist_ok=True)
    for view in ('front','side','back'):
        image,rig,layers=demo(view);image.save(dest/f'{view}.png');(dest/f'{view}.rig.json').write_text(json.dumps(rig,indent=2))
