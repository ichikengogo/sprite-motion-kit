"""Source-preserving drawn-cel walk assembly. Numeric checks are NOT visual approval."""
import argparse
import hashlib
import json
import math
import io
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

GATES = ('identity', 'phase_ownership', 'waist_connection', 'cloth_coverage', 'motion_contact', 'identity_stability')
TEMPORAL_GATES = ('motion_contact','identity_stability')
PHASES = {'contact', 'down', 'passing', 'up', 'transition'}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def confined(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError('Asset paths must be nonempty relative paths')
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Asset path escapes project directory')
    if not path.is_file():
        raise ValueError('Missing asset: ' + name)
    return path

def read(project):
    path = Path(project).resolve()
    p = json.loads(path.read_text())
    return path, p

def asset_names(p):
    return sorted(set(([p['upperCel']] if p.get('representation','shared-upper-lower') == 'shared-upper-lower' else []) + [r['source'] for r in p['registration']] + p.get('identitySources', [])))

def pin_sources(project):
    path, p = read(project)
    p['sourcePins'] = {n: digest(confined(path.parent, n)) for n in asset_names(p)}
    path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + '\n')
    return p['sourcePins']

def vector(v, length, name, integer=False):
    if not isinstance(v, list) or len(v) != length or any(isinstance(x, bool) or not isinstance(x, (int,float)) or not math.isfinite(x) for x in v):
        raise ValueError('Invalid ' + name)
    if integer and any(not isinstance(x, int) for x in v):
        raise ValueError(name + ' must contain integers')

def validate(project):
    path, p = read(project)
    if p.get('schema') != 'drawn-cel-loop/1':
        raise ValueError('Unsupported schema')
    vector(p.get('canvas'), 2, 'canvas', True)
    if any(x <= 0 or x > 8192 for x in p['canvas']): raise ValueError('Invalid canvas bounds')
    regs = p.get('registration')
    if not isinstance(regs, list) or not 2 <= len(regs) <= 256 or type(p.get('frames')) is not int or p.get('frames') != len(regs):
        raise ValueError('Frame count mismatch')
    durations = p.get('durationsMs')
    if not isinstance(durations, list) or len(durations) != len(regs) or any(type(d) is not int or d <= 0 or d % 10 for d in durations):
        raise ValueError('durationsMs must be positive exact GIF multiples of 10 ms')
    if 'durationSeconds' in p and abs(sum(durations)/1000-p['durationSeconds']) > 1e-8:
        raise ValueError('Duration mismatch')
    if not isinstance(p.get('identitySources'),list) or not p['identitySources']: raise ValueError('identitySources required: immutable original identity references')
    mode=p.get('representation','shared-upper-lower')
    if mode not in ('shared-upper-lower','coherent-full-cel'): raise ValueError('Invalid representation')
    if mode=='shared-upper-lower':
        for field in ('upperTranslationX','upperAnchorY'):
            if type(p.get(field)) is not int: raise ValueError(field + ' must be integer')
    elif p.get('connectionRestorePolygons') or any(r.get('clipRects') or r.get('clipOldRightHem') for r in regs):
        raise ValueError('Full cels do not use lower-body clipping or connection restoration')
    names = asset_names(p)
    for n in names:
        q = confined(path.parent, n)
        if p.get('sourcePins', {}).get(n) != digest(q): raise ValueError('Missing or stale source pin: '+n)
        with Image.open(q) as im:
            if im.width > 8192 or im.height > 8192: raise ValueError('Asset too large')
    for r in regs:
        if r.get('clipOldRightHem'): raise ValueError('Migrate legacy clipOldRightHem to explicit source-space clipRects')
        for key in (('sourceWaist','translation','targetWaist') if mode=='shared-upper-lower' else ('translation',)): vector(r.get(key),2,key,True)
        scale = r.get('uniformLowerScale') if mode=='shared-upper-lower' else r.get('scale')
        if isinstance(scale,bool) or not isinstance(scale,(int,float)) or not math.isfinite(scale) or not 0 < scale <= 8: raise ValueError('Invalid uniformLowerScale')
        with Image.open(confined(path.parent,r['source'])) as im:
            if mode=='shared-upper-lower':
                sx,sy=r['sourceWaist']
                if not (0 <= sx < im.width and 0 <= sy < im.height): raise ValueError('sourceWaist outside source')
            if min(round(v*scale) for v in im.size) < 1: raise ValueError('Scaled asset rounds to zero size')
            if max(im.size)*scale > 16384: raise ValueError('Scaled asset too large')
        for rect in r.get('clipRects',[]):
            vector(rect,4,'clipRects',True)
            if rect[0] < 0 or rect[1] < 0 or rect[2] <= rect[0] or rect[3] <= rect[1]: raise ValueError('Invalid clip rectangle')
    for key, poly in p.get('connectionRestorePolygons',{}).items():
        if not key.isdigit() or not 0 <= int(key) < len(regs) or not isinstance(poly,list) or len(poly)<3: raise ValueError('Invalid connection polygon')
        for point in poly: vector(point,2,'connection polygon point',True)
    phases=p.get('phaseMetadata')
    if not isinstance(phases,list) or len(phases)!=len(regs): raise ValueError('phaseMetadata required for every cel')
    owners=p.get('legOwners',['near','far'])
    if not isinstance(owners,list) or len(owners)!=2 or any(not isinstance(x,str) or not x.strip() for x in owners) or owners[0]==owners[1]: raise ValueError('legOwners must name two distinct source leg identities')
    for row in phases:
        if row.get('phase') not in PHASES or {row.get('supportOwner'),row.get('swingOwner')} != set(owners): raise ValueError('Invalid phase/leg ownership')
    if {r['supportOwner'] for r in phases} != set(owners): raise ValueError('Support owner never alternates')
    # Explicit contact keys must alternate owner, including across the loop.
    contacts=[r['supportOwner'] for r in phases if r['phase']=='contact']
    if len(contacts)<2 or any(contacts[i]==contacts[(i+1)%len(contacts)] for i in range(len(contacts))):
        raise ValueError('Contact ownership must alternate across the cycle')
    for probe in p.get('coverageProbes',[]):
        if type(probe.get('frame')) is not int or not 0 <= probe['frame'] < len(regs): raise ValueError('Invalid coverage probe frame')
        if type(probe.get('minAlpha',255)) is not int or not 1 <= probe.get('minAlpha',255) <= 255: raise ValueError('Invalid coverage minAlpha')
        if not isinstance(probe.get('points'),list) or not probe['points']: raise ValueError('Empty coverage probe')
        for point in probe['points']:
            vector(point,2,'coverage point',True)
            if not 0 <= point[0] < p['canvas'][0] or not 0 <= point[1] < p['canvas'][1]: raise ValueError('Coverage point outside canvas')
    return p

def assemble(p, root):
    if p.get('representation')=='coherent-full-cel':
        frames=[]
        for r in p['registration']:
            raw=Image.open(confined(root,r['source'])).convert('RGBA');scale=r['scale'];cel=raw.resize((round(raw.width*scale),round(raw.height*scale)),Image.Resampling.LANCZOS);frame=Image.new('RGBA',tuple(p['canvas']));frame.alpha_composite(cel,tuple(r['translation']));frames.append(frame)
        return frames
    upper=Image.open(confined(root,p['upperCel'])).convert('RGBA')
    frames=[]
    for i,r in enumerate(p['registration']):
        raw=Image.open(confined(root,r['source'])).convert('RGBA');a=np.array(raw);sx,sy=r['sourceWaist'];a[:sy,:,3]=0
        if r.get('clipOldRightHem'): raise ValueError('Migrate legacy clipOldRightHem to explicit source-space clipRects')
        for x0,y0,x1,y1 in r.get('clipRects',[]):a[y0:y1,x0:x1,3]=0
        scale=r['uniformLowerScale'];size=(round(raw.width*scale),round(raw.height*scale))
        low=Image.fromarray(a).resize(size,Image.Resampling.LANCZOS);f=Image.new('RGBA',tuple(p['canvas']))
        f.alpha_composite(low,tuple(r['translation']));f.alpha_composite(upper,(p['upperTranslationX'],r['targetWaist'][1]-p['upperAnchorY']))
        poly=p.get('connectionRestorePolygons',{}).get(str(i))
        if poly:
            mask=Image.new('L',raw.size);ImageDraw.Draw(mask).polygon([tuple(x) for x in poly],fill=255)
            a=np.array(raw);a[:,:,3]=np.minimum(a[:,:,3],np.array(mask));low=Image.fromarray(a).resize(size,Image.Resampling.LANCZOS)
            backing=Image.new('RGBA',f.size);backing.alpha_composite(low,tuple(r['translation']));backing.alpha_composite(f);f=backing
        frames.append(f)
    return frames

def render_frames(project):
    p=validate(project);frames=assemble(p,Path(project).resolve().parent)
    n=len(frames)
    if n%2==0 and all(frames[i].tobytes()==frames[i+n//2].tobytes() for i in range(n//2)):
        raise ValueError('Repeated identical half-cycle: two leg roles were not visibly exchanged')
    for probe in p.get('coverageProbes',[]):
        f=frames[probe['frame']]
        for point in probe['points']:
            if f.getpixel(tuple(point))[3] < probe.get('minAlpha',255):
                raise ValueError('Coverage alpha probe failed: frame '+str(probe['frame'])+' point '+str(point)+'; alpha is not semantic clothing validation')
    return frames

def renderer_fingerprint():
    return digest(Path(__file__))

def fingerprint(project):
    path,p=read(project)
    payload={'renderer':renderer_fingerprint(),'project':p,'assets':{n:digest(confined(path.parent,n)) for n in asset_names(p)}}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def review_path(project):
    return Path(str(Path(project).resolve())+'.reviews.json')

def _preview_bytes(frames,p,height):
    w,h=p['canvas'];size=(max(1,round(w*height/h)),height);gif=[]
    for f in frames:
        b=Image.new('RGBA',size,'#dddddd');b.alpha_composite(f.resize(size,Image.Resampling.LANCZOS));gif.append(b.convert('RGB'))
    stream=io.BytesIO();gif[0].save(stream,format='GIF',save_all=True,append_images=gif[1:],duration=p['durationsMs'],loop=0,disposal=2);return stream.getvalue()

def _gif_signature(source):
    with Image.open(source) as im:
        if im.format!='GIF' or im.n_frames<2:raise ValueError('Continuous observation artifact must be an animated GIF, not extracted stills')
        frames=[]
        for i in range(im.n_frames):
            im.seek(i);frames.append((im.info.get('duration'),hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest()))
        return im.size,im.info.get('loop'),frames

def _temporal_reason(project,row):
    o=row.get('observation',{})
    if o.get('method')!='continuous-playback':return 'UNREVIEWED: continuous playback was not observed; sampled stills/durations/pixel equality are insufficient'
    if not isinstance(o.get('reviewer'),str) or not o['reviewer'].strip():return 'BLOCKED: named reviewer required'
    if not isinstance(o.get('methodTool'),str) or not o['methodTool'].strip():return 'BLOCKED: actual observation tool or method required'
    if not isinstance(o.get('continuityFindings'),str) or not o['continuityFindings'].strip():return 'BLOCKED: concrete continuity findings required'
    if type(o.get('playbackSpeed')) not in (int,float) or o['playbackSpeed']!=1.0:return 'BLOCKED: normal-speed (1.0x) observation required'
    observations=o.get('observations')
    if not isinstance(observations,list):return 'BLOCKED: native and 128 playback observations required'
    by_display={r.get('display'):r for r in observations if isinstance(r,dict)}
    if set(by_display)!={'native','128'} or len(observations)!=2:return 'BLOCKED: exactly native and 128 playback observations required'
    p=validate(project);frames=render_frames(project);root=Path(project).resolve().parent
    for display,height in [('native',p['canvas'][1]),('128',128)]:
        r=by_display[display]
        if type(r.get('completeLoopsObserved')) is not int or r['completeLoopsObserved'] < 1:return 'BLOCKED: actual complete loop count required in '+display
        if r.get('loopObserved') is not True:return 'BLOCKED: loop boundary must be observed in '+display
        try:
            artifact=confined(root,r['artifact'])
            if digest(artifact)!=r.get('artifactSha256'):return 'BLOCKED: playback artifact hash changed'
            if _gif_signature(artifact)!=_gif_signature(io.BytesIO(_preview_bytes(frames,p,height))):return 'BLOCKED: playback artifact differs from current project animation/timing'
        except (OSError,ValueError,KeyError):return 'BLOCKED: valid current animated playback artifact required'
    return None

def reviews_report(project):
    q=review_path(project);data=json.loads(q.read_text()) if q.exists() else {};fp=fingerprint(project);result={}
    for gate in GATES:
        row=data.get(gate,{})
        try: valid=row.get('fingerprint')==fp and digest(confined(Path(project).resolve().parent,row['evidence']))==row.get('evidenceSha256') and bool(row.get('note'))
        except (KeyError,OSError,ValueError):valid=False
        reason=None if valid else 'UNREVIEWED: missing or stale review/evidence'
        if valid and gate in TEMPORAL_GATES:reason=_temporal_reason(project,row)
        result[gate]={'valid':valid and reason is None,'status':'reviewed' if valid and reason is None else ('blocked' if reason and reason.startswith('BLOCKED') else 'unreviewed'),'reason':reason,'kind':'human observation assertion; file validation cannot prove a person actually watched playback'}
    return result

def reviews_status(project):
    return {gate:row['valid'] for gate,row in reviews_report(project).items()}

def _store_evidence(project,src):
    root=Path(project).resolve().parent;src=Path(src).resolve()
    if not src.is_file():raise ValueError('Review evidence missing')
    sha=digest(src);_,p=read(project);relative=str(src.relative_to(root)) if src.is_relative_to(root) else None
    if relative is not None and p.get('sourcePins',{}).get(relative)==sha:dest=src
    else:
        dest=root/'review-evidence'/(sha+src.suffix);dest.parent.mkdir(exist_ok=True)
        if not dest.exists():dest.write_bytes(src.read_bytes())
    return str(dest.relative_to(root)),sha

def record_review(project,gate,evidence,note,observation=None):
    render_frames(project)
    if gate not in GATES or not isinstance(note,str) or len(note.strip())<12:raise ValueError('Valid gate and meaningful human review note required')
    relative,sha=_store_evidence(project,evidence)
    if observation is None:observation={'method':'unknown','reviewer':None,'playbackSpeed':None,'observations':[]}
    if not isinstance(observation,dict) or observation.get('method') not in ('continuous-playback','sampled-stills','unknown'):raise ValueError('Invalid structured observation method')
    observation=json.loads(json.dumps(observation))
    if not isinstance(observation.get('observations',[]),list):raise ValueError('observations must be a list')
    for item in observation.get('observations',[]):
        if not isinstance(item,dict) or 'artifact' not in item:raise ValueError('Observation artifact required')
        item['artifact'],item['artifactSha256']=_store_evidence(project,item['artifact'])
    q=review_path(project);data=json.loads(q.read_text()) if q.exists() else {}
    row={'fingerprint':fingerprint(project),'evidence':relative,'evidenceSha256':sha,'note':note.strip(),'observation':observation,'kind':'human assertion, not automated visual recognition'}
    data[gate]=row;q.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    return {**row,'gateStatus':reviews_report(project)[gate]}

def export_project(project,out,mode='draft'):
    if mode not in ('draft','reviewed-draft'): raise ValueError('Invalid mode')
    frames=render_frames(project);p=validate(project);reviews=reviews_status(project)
    if mode=='reviewed-draft' and not all(reviews.values()): raise ValueError('Missing or stale human review gates: '+', '.join(k for k,v in reviews.items() if not v))
    out=Path(out)
    if out.exists(): raise ValueError('Use a new output directory; existing exports are immutable')
    out.mkdir(parents=True);w,h=p['canvas'];cols=min(5,len(frames));rows=math.ceil(len(frames)/cols)
    sheet=Image.new('RGBA',(w*cols,h*rows))
    for i,f in enumerate(frames):f.save(out/f'frame-{i:02}.png');sheet.alpha_composite(f,((i%cols)*w,(i//cols)*h))
    sheet.save(out/'sheet.png')
    for bg,name in [('#00bfbf','cyan'),('#ff00ff','magenta'),('#000000','black')]:
        b=Image.new('RGBA',sheet.size,bg);b.alpha_composite(sheet);b.save(out/f'review-{name}.png')
    for height,name in [(h,'native'),(128,'128')]:
        (out/f'preview-{name}.gif').write_bytes(_preview_bytes(frames,p,height))
    report={'schema':'drawn-cel-export/1','quality':mode,'rendererFingerprint':renderer_fingerprint(),'fingerprint':fingerprint(project),'frames':len(frames),'durationsMs':p['durationsMs'],'humanGates':reviews,'humanReviewDetails':reviews_report(project),'frameSha256':[hashlib.sha256(f.tobytes()).hexdigest() for f in frames], 'interpolation':'none; only actual authored cells exported','automaticChecks':['schema','asset hash freshness','source path confinement','declared owner alternation','nonidentical raster half-cycles','optional declared alpha coverage probes'],'notAutomaticallyVerified':['natural gait','semantic garment coverage','waist connection or horizontal crop appearance','skin versus fabric','foot sliding','identity beyond shared cel'],'sourcePins':p['sourcePins']}
    (out/'export.json').write_text(json.dumps(report,indent=2));return report

def write_template(out):
    out=Path(out)
    if out.exists(): raise ValueError('Template destination already exists')
    p={'schema':'drawn-cel-loop/1','canvas':[512,512],'frames':8,'durationSeconds':1,
       'durationsMs':[120,130]*4,'identitySources':['sources/original.png'],'upperCel':'sources/shared-upper.png',
       'upperTranslationX':0,'upperAnchorY':0,'sourcePins':{},'connectionRestorePolygons':{},
       'registration':[{'source':f'sources/cel-{i:02}.png','sourceWaist':[0,0],'uniformLowerScale':1.0,
                        'translation':[0,0],'targetWaist':[0,0],'clipRects':[]} for i in range(8)],
       'phaseMetadata':[{'phase':['contact','down','passing','up'][i%4],
                         'supportOwner':'near' if i<4 else 'far','swingOwner':'far' if i<4 else 'near'} for i in range(8)],
       'status':'INCOMPLETE TEMPLATE: replace dimensions, source ownership, registration and actual role observations; no art supplied',
       'limitations':['No automatic raster generation or interpolation. Source artwork edits require an authorized drawing or image-editing workflow. Phase labels are declarations, not visual proof.']}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(p,indent=2)+'\n');return {'template':str(out),'runnable':False,'reason':'Supply originals and authored cels, calibrate registration, then pin intentional sources.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for cmd in ('pin','validate','render','review','template'):
        s=sub.add_parser(cmd);s.add_argument('project')
        if cmd=='render':s.add_argument('--out',required=True);s.add_argument('--mode',choices=['draft','reviewed-draft'],default='draft')
        if cmd=='review':s.add_argument('--gate',choices=GATES,required=True);s.add_argument('--evidence',required=True);s.add_argument('--note',required=True);s.add_argument('--observation-json')
    a=parser.parse_args()
    try:
        if a.command=='template':result=write_template(a.project)
        elif a.command=='pin':result=pin_sources(a.project)
        elif a.command=='validate':render_frames(a.project);result={'valid':True,'humanGates':reviews_status(a.project),'visualApproval':False}
        elif a.command=='review':result=record_review(a.project,a.gate,a.evidence,a.note,json.loads(Path(a.observation_json).read_text()) if a.observation_json else None)
        else:result=export_project(a.project,a.out,a.mode)
        print(json.dumps(result,indent=2,ensure_ascii=False))
    except (ValueError,KeyError,OSError,TypeError) as e:parser.exit(2,str(e)+'\n')

if __name__=='__main__': main()
