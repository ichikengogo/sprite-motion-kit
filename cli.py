"""Demo exports or explicitly confirmed custom normalized PNG + rig."""
import argparse,json
from pathlib import Path
from PIL import Image
from demo import demo
from motion import validate,cutouts,export,render,require_ready

def main():
    p=argparse.ArgumentParser();p.add_argument('--view',choices=['front','side','back'],default='side');p.add_argument('--action',choices=['walk','dash'],default='walk');p.add_argument('--output',default='output');p.add_argument('--image');p.add_argument('--rig');p.add_argument('--walk-style',choices=['cautious','purposeful','wide-stable','simple']);p.add_argument('--motion-scale',type=float);a=p.parse_args()
    if bool(a.image)!=bool(a.rig):p.error('--image and --rig must be used together')
    if a.image:
        im=Image.open(a.image).convert('RGBA');rig=json.loads(Path(a.rig).read_text());validate(rig,im)
        require_ready(rig)
        if im.getchannel('A').getextrema()[0]==255:p.error('Transparent PNG required')
        layers=cutouts(im,rig)
        if any(x.getbbox() is None for x in layers.values()):p.error('Empty part mask')
    else:im,rig,layers=demo(a.view)
    if a.walk_style is not None:rig['walkStyle']=a.walk_style
    if a.motion_scale is not None:rig['motionScale']=a.motion_scale
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True);sheet,meta=export(rig,layers,a.action);stem=f'{rig["view"]}-{a.action}'
    sheet.save(out/f'{stem}.png');(out/f'{stem}.json').write_text(json.dumps(meta,indent=2))
    frames=[];count=len(meta['frames'])
    for i in range(count):
        frame,_=render(rig,layers,a.action,i/count);bg=Image.new('RGBA',frame.size,'#20303f');bg.alpha_composite(frame);frames.append(bg.convert('RGB'))
    frames[0].save(out/f'{stem}-preview.gif',save_all=True,append_images=frames[1:],duration=[10*(round((i+1)*meta['duration']*100/count)-round(i*meta['duration']*100/count)) for i in range(count)],loop=0)
    print(json.dumps({'output':str(out),'quality':meta['quality']},ensure_ascii=False))
if __name__=='__main__':main()
