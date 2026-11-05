"""Original geometric test fixtures, not generated character art or gait-quality evidence.

No network, API key, external image or private artwork is used. Primitive diagrams
exercise differing source proportions, garments, contacts, views and cel counts.
"""
from pathlib import Path
import argparse, json, math, shutil
from PIL import Image, ImageDraw
import drawn_cel

SPECS = {
 'tall-tunic': {'canvas':[192,288], 'frames':8, 'durationsMs':[120,130]*4,
                'bodyWidth':36,'headRadius':17,'hipY':164,'groundY':266,
                'garment':'long teal tunic over narrow violet trousers', 'held':False,
                'representation':'coherent-full-cel'},
 'broad-overalls': {'canvas':[256,224], 'frames':10, 'durationsMs':[100]*10,
                   'bodyWidth':68,'headRadius':22,'hipY':139,'groundY':207,
                   'garment':'orange short overalls over blue shirt', 'held':True,
                   'representation':'shared-upper-lower'}
}

def phases(count):
    half = ['contact','down','passing','up'] if count==8 else ['contact','down','transition','passing','up']
    return half*2

def draw(spec, view, index=0, neutral=False, upper_only=False):
    """Render original code-native shape diagrams with visible limb identities."""
    w,h=spec['canvas'];im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
    cx=w//2;hip=spec['hipY'];g=spec['groundY'];bw=spec['bodyWidth'];hr=spec['headRadius']
    side=view=='side';back=view=='back';n=spec['frames'];t=0 if neutral else 2*math.pi*index/n
    bob=0 if neutral or spec['held'] else round(2*math.cos(t*2))
    hy=hip+bob;neck=round(h*.23);head=(cx,neck-hr)
    # Anatomical legs stay red/blue in every frame; side far limb is always behind.
    legs=[('far',(61,92,157,255),1),('near',(111,74,149,255),-1)]
    if not upper_only:
      for owner,color,sgn in legs:
        spread=0 if neutral else math.cos(t)*sgn
        if side:
          x0=cx+sgn*3;x1=cx+round(spread*bw*.7)
        else:
          x0=cx+sgn*bw//4;x1=x0+round(spread*bw*.12)
        lift=0 if neutral else max(0,math.sin(t)*sgn)*h*.045
        yy=g-round(lift);knee=(round((x0+x1)/2),round((hy+yy)/2))
        width=max(8,bw//4)
        d.line([(x0,hy-4),knee,(x1,yy-5)],fill=color,width=width)
        # source-dependent garment hem, visibly different across profiles
        cuffy=hy+int((g-hy)*(.58 if not spec['held'] else .32))
        cuffx=round(x0+(x1-x0)*(cuffy-hy)/(g-hy))
        d.line([(x0,hy-5),(cuffx,cuffy)],fill=(30,126,120,255) if not spec['held'] else (219,113,39,255),width=width+3)
        d.rectangle((x1-width//2-3,yy-7,x1+width//2+6,yy),fill=color,outline=(25,28,34,255),width=1)
    # torso/upper can be a true shared cel (held profile) or authored whole-frame part.
    shoulder=neck+hr//2;torso=(cx-bw//2,shoulder+bob,cx+bw//2,hy+3)
    d.rounded_rectangle(torso,radius=5,fill=(30,126,120,255) if not spec['held'] else (43,110,174,255),outline=(25,28,34,255),width=2)
    if spec['held']:
      d.rectangle((cx-bw//3,shoulder+15,cx+bw//3,hy+3),fill=(219,113,39,255))
      d.line((cx-bw//3,shoulder,cx-bw//3,hy),fill=(219,113,39,255),width=6)
      d.line((cx+bw//3,shoulder,cx+bw//3,hy),fill=(219,113,39,255),width=6)
    if back:
      d.line((cx,shoulder+8+bob,cx,hy-5),fill=(20,70,85,255),width=2)
    elif not side:
      d.ellipse((cx-3,shoulder+12+bob,cx+3,shoulder+18+bob),fill=(244,224,116,255))
    # Free arms alternate, held arms retain source tool contact.
    for sgn in (-1,1):
      sx=cx+sgn*bw//2;sy=shoulder+8+bob
      if spec['held']:ex=cx+sgn*12;ey=round((shoulder+hy)*.55)
      else:ex=sx+round((0 if neutral else math.sin(t))*sgn*12);ey=hy-12+bob
      d.line((sx,sy,ex,ey),fill=(227,194,157,255),width=max(6,bw//7))
    if spec['held']:
      d.rectangle((cx-21,round((shoulder+hy)*.55)-5,cx+21,round((shoulder+hy)*.55)+5),fill=(76,74,68,255))
    d.ellipse((head[0]-hr,head[1]-hr+bob,head[0]+hr,head[1]+hr+bob),fill=(227,194,157,255),outline=(25,28,34,255),width=2)
    if not back:
      ex=cx-hr//2 if side else cx-hr//3
      d.ellipse((ex-2,head[1]-2+bob,ex+2,head[1]+2+bob),fill=(25,28,34,255))
      if not side:d.ellipse((cx+hr//3-2,head[1]-2+bob,cx+hr//3+2,head[1]+2+bob),fill=(25,28,34,255))
    if upper_only:
      # Source cel ends inside the garment overlap, never at an arbitrary exterior shelf.
      im=im.crop((0,0,w,hy+4))
    return im

def build_assets(out):
    out=Path(out)
    if out.exists():raise ValueError('Use new fixture directory')
    out.mkdir(parents=True);summary={}
    for name,spec in SPECS.items():
      root=out/name;root.mkdir();originals=root/'originals';originals.mkdir();projects={}
      for view in ['front','back','side']:
        original=draw(spec,view,neutral=True);original.save(originals/(view+'.png'))
        pdir=root/'authored'/view;pdir.mkdir(parents=True);shutil.copy2(originals/(view+'.png'),pdir/'original.png')
        upper=draw(spec,view,neutral=True,upper_only=True);upper.save(pdir/'upper.png')
        regs=[];n=spec['frames']
        for i in range(n):
          draw(spec,view,i).save(pdir/f'cel-{i:02}.png')
          regs.append({'source':f'cel-{i:02}.png','sourceWaist':[spec['canvas'][0]//2,spec['hipY']],
                       'uniformLowerScale':1.0,'translation':[0,0],'targetWaist':[spec['canvas'][0]//2,spec['hipY']], 'clipRects':[]})
        owners=['near','far'] if view=='side' else ['anatomical-left','anatomical-right']
        if spec['representation']=='coherent-full-cel':
          regs=[{'source':x['source'],'scale':1.0,'translation':[0,0]} for x in regs]
        project={'schema':'drawn-cel-loop/1','representation':spec['representation'],'view':view,
                 'canvas':spec['canvas'],'frames':n,'durationsMs':spec['durationsMs'],'durationSeconds':sum(spec['durationsMs'])/1000,
                 'identitySources':['original.png'],'upperCel':'upper.png','upperTranslationX':0,'upperAnchorY':spec['hipY'],
                 'registration':regs,'legOwners':owners,'phaseMetadata':[{'phase':phase,'supportOwner':owners[0] if i<n//2 else owners[1],'swingOwner':owners[1] if i<n//2 else owners[0]} for i,phase in enumerate(phases(n))],
                 'fixtureOnly':True,'limitations':['Original geometric test diagrams, not artistic walk-quality evidence.']}
        if spec['representation']=='coherent-full-cel':
          for key in ('upperCel','upperTranslationX','upperAnchorY'):project.pop(key)
        (pdir/'project.json').write_text(json.dumps(project,indent=2));drawn_cel.pin_sources(pdir/'project.json');projects[view]=str(pdir/'project.json')
      summary[name]={'spec':spec,'originals':str(originals),'projects':projects}
    portable={name:{'spec':item['spec'],'originals':name+'/originals','projects':{v:name+'/authored/'+v+'/project.json' for v in item['projects']}} for name,item in summary.items()}
    (out/'fixtures.json').write_text(json.dumps(portable,indent=2));return summary

def run_workflows(fixtures, output):
    """Exercise same intake/plan/bind/render entry with synthetic, non-art inputs."""
    import character_workflow as workflow
    output=Path(output)
    if output.exists():raise ValueError('Use a new workflow output directory')
    output.mkdir(parents=True);reports={}
    for name,item in fixtures.items():
      spec=item['spec'];originals=Path(item['originals']);workspace=output/name
      path=Path(workflow.init_workspace({v:originals/(v+'.png') for v in ('front','side','back')},workspace))
      profile=json.loads(path.read_text())
      profile.update(identity={'descriptors':['original geometric test diagram',name]},
        proportions={'notes':f"canvas {spec['canvas']}; body width {spec['bodyWidth']}; technical fixture only"},
        clothing=[{'name':spec['garment'],'boundary':'connected torso-to-leg geometric silhouette','length':'tunic below hip' if not spec['held'] else 'short overall legs'}],
        accessories=[{'name':'rectangular test tool','behavior':'rigid'}] if spec['held'] else [],
        contacts={'armMode':'held' if spec['held'] else 'free','held':['both hands to tool'] if spec['held'] else []},
        timing={'durationsMs':spec['durationsMs'],'phases':phases(spec['frames'])})
      for view in ('front','side','back'):
        owners=['near','far'] if view=='side' else ['anatomical-left','anatomical-right']
        profile['views'][view]={'facing':'left' if view=='side' else view,'representation':spec['representation'],
          'ownership':{'ownerA':owners[0],'ownerB':owners[1],'basis':'near-far' if view=='side' else 'anatomical-left-right'}}
      path.write_text(json.dumps(profile,indent=2))
      workflow.record_intake(path,workspace/'inputs/side.png','Technical synthetic fixture intake: original primitive sources, different proportions/costumes and declared contacts; not human artistic quality approval.')
      requests=workflow.plan(path)
      for view in ('front','side','back'):
        source=Path(item['projects'][view]).parent
        if spec['representation']=='coherent-full-cel':
          target=workspace/'authored-cels'/view;target.mkdir(parents=True)
          for cel in sorted(source.glob('cel-*.png')):shutil.copy2(cel,target/cel.name)
          workflow.register_cels(path,view,target)
        else:
          target=workspace/'authored'/view;shutil.copytree(source,target)
          workflow.bind(path,view,target/'project.json')
      report=workflow.render_all(path,workspace/'rendered',mode='draft')
      reports[name]={'workspace':str(workspace),'profile':str(path),'canvas':spec['canvas'],'framesPerView':spec['frames'],
                     'views':['front','side','back'],'representation':spec['representation'],'status':'technical pipeline fixture only, not artistic quality approval'}
    portable={name:{**row,'workspace':name,'profile':name+'/character-profile.json'} for name,row in reports.items()}
    (output/'technical-validation.json').write_text(json.dumps(portable,indent=2))
    return reports

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--workflow-out');a=p.parse_args()
    fixtures=build_assets(a.out)
    print(json.dumps(run_workflows(fixtures,a.workflow_out) if a.workflow_out else fixtures,indent=2))
if __name__=='__main__':main()
