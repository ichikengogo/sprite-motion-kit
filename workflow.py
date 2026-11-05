"""Three-view intake and evidence-tracked manual-calibration draft export. No network service required."""
import argparse, base64, hashlib, io, json, threading, urllib.request, shutil, tempfile
from pathlib import Path
from PIL import Image
VIEWS=('front','side','back')
GATES=('source_correspondence','ownership','landmarks','hidden_parts','proportions','outlines','cloth_coverage','heels','whole_cycle')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2))
def init(out,inputs):
    out=Path(out)
    if out.exists():raise ValueError('Output must be a new directory; originals are never overwritten')
    records={}
    for view in VIEWS:
        p=Path(inputs[view]);im=Image.open(p)
        if im.format!='PNG':raise ValueError('PNG only')
        im.load();a=im.convert('RGBA').getchannel('A')
        if a.getbbox() is None or a.getextrema()[0]==255:raise ValueError('Nonempty transparent PNG required; no background removal')
        if max(im.size)>8192:raise ValueError('Image dimensions exceed 8192')
        records[view]={'input':f'inputs/{view}.png','sha256':digest(p),'size':list(im.size),'status':'needs_annotation','engine_reference_validated':view=='side','review':{}}
    if len({r['sha256'] for r in records.values()})!=3:raise ValueError('Three distinct view images required; duplicated sources rejected')
    out.mkdir(parents=True);(out/'inputs').mkdir()
    for view in VIEWS:(out/'inputs'/f'{view}.png').write_bytes(Path(inputs[view]).read_bytes())
    m={'schema':'sprite-motion-workflow/2','views':records,'claims':'Manual assisted workflow; front/back high-quality pipeline not validated; all exports draft'};write(out/'manifest.json',m);return m

def decode(encoded):
    if not isinstance(encoded,str) or not encoded.startswith('data:image/png;base64,'):
        raise ValueError('Embedded PNG data URL required')
    im=Image.open(io.BytesIO(base64.b64decode(encoded.split(',',1)[1],validate=True)))
    if im.format!='PNG':raise ValueError('PNG only')
    im.load();return im.convert('RGBA')

def same_pixels(a,b):
    return a.size==b.size and a.convert('RGBA').tobytes()==b.convert('RGBA').tobytes()

def sources_current(p,m):
    for record in m['views'].values():
        if digest(p.parent/record['input'])!=record['sha256']:
            raise ValueError('Intake source changed; start a new intake and re-review correspondence')

def evidence_current(r,base):
    e=base/r.get('evidence','')
    return bool(r.get('note','').strip()) and e.is_file() and digest(e)==r.get('sha256')

def archive_evidence(p,evidence):
    source=Path(evidence);h=digest(source)
    relative=Path('evidence')/(h+source.suffix)
    target=p.parent/relative;target.parent.mkdir(exist_ok=True)
    if source.resolve()!=target.resolve():shutil.copyfile(source,target)
    return {'evidence':relative.as_posix(),'sha256':h}

def identity(manifest,evidence,note):
    p=Path(manifest);m=read(p);sources_current(p,m)
    if not note.strip() or not Path(evidence).is_file():raise ValueError('Human identity/proportions review note and evidence required')
    m['identity_review']={'note':note,**archive_evidence(p,evidence),'sources':{v:m['views'][v]['sha256'] for v in VIEWS}}
    write(p,m)

def require_identity(m,base):
    r=m.get('identity_review',{})
    if not evidence_current(r,base) or r.get('sources')!={v:m['views'][v]['sha256'] for v in VIEWS}:
        raise ValueError('Review all three source identities/proportions before registration: workflow.py identity MANIFEST --evidence FILE --note TEXT')

def bind(manifest,project):
    p=Path(manifest);m=read(p);data=read(project)
    if not isinstance(data.get('projects'),dict):raise ValueError('Expected browser saved project with projects')
    sources_current(p,m);require_identity(m,p.parent)
    from motion import validate,require_ready
    for view in VIEWS:
        item=data['projects'].get(view,{})
        rig=item.get('rig',{})
        if rig.get('view')!=view or item.get('demo'):raise ValueError('Registered non-demo rig required for '+view)
        validate(rig);require_ready(rig)
        source=Image.open(p.parent/m['views'][view]['input']).convert('RGBA')
        candidates=[item.get('image')]
        if isinstance(item.get('original'),dict):candidates.append(item['original'].get('image'))
        if not any(same_pixels(source,decode(c)) for c in candidates if c):
            raise ValueError('Source mismatch for '+view+': use the actual original or exact normalized source, never transfer another character rig')
        validate(rig,decode(item['image']))
    target=p.parent/'working-project.json'
    if Path(project).resolve()!=target.resolve():target.write_bytes(Path(project).read_bytes())
    m['project']={'path':target.name,'sha256':digest(target)}
    for r in m['views'].values():r['review']={};r['status']='registered_needs_review'
    write(p,m);return m

def attest(manifest,gate,evidence,note,action,view="side"):
    if view not in VIEWS or gate not in GATES or action not in ("walk","dash"):raise ValueError("Unknown review scope")
    p=Path(manifest);m=read(p)
    if not note.strip():raise ValueError('Human review note required')
    if 'project' not in m:raise ValueError('Bind saved project first')
    e=Path(evidence).resolve()
    if not e.is_file():raise ValueError('Evidence file required')
    sources_current(p,m);require_identity(m,p.parent)
    if digest(p.parent/m['project']['path'])!=m['project']['sha256']:raise ValueError('Project changed; rebind and re-review')
    m['views'][view]['review'].setdefault(action,{})[gate]={**archive_evidence(p,e),'note':note,'project_sha256':m['project']['sha256']}
    write(p,m)

def gif_durations(times,duration):
    # GIF centiseconds cannot represent 125ms; cumulative rounding preserves cycle length.
    ticks=[round(t*100) for t in [*times,duration]]
    return [10*(b-a) for a,b in zip(ticks,ticks[1:])]

def save_preview(frames,times,duration,path):
    opaque=[]
    for frame in frames:
        bg=Image.new('RGBA',frame.size,'#dddddd');bg.alpha_composite(frame)
        opaque.append(bg.convert('RGB'))
    opaque[0].save(path,save_all=True,append_images=opaque[1:],duration=gif_durations(times,duration),loop=0,disposal=2,optimize=False)

def comparison_preview(out):
    from PIL import ImageDraw
    metas={v:read(out/v/'animation.json') for v in VIEWS}
    duration=metas['front']['duration']
    if any(abs(m['duration']-duration)>1e-6 for m in metas.values()):raise ValueError('Comparison requires equal cycle durations')
    times=sorted({f['time'] for m in metas.values() for f in m['frames']})
    frames=[]
    for t in times:
        board=Image.new('RGBA',(384*3,410),'#dddddd');draw=ImageDraw.Draw(board)
        for i,v in enumerate(VIEWS):
            f=max((f for f in metas[v]['frames'] if f['time']<=t+1e-8),key=lambda f:f['time'])
            im=Image.open(out/v/('frame-%02d.png'%f['index'])).convert('RGBA')
            board.alpha_composite(im,(384*i,26));draw.text((384*i+12,8),v+' / DRAFT',fill='black')
        frames.append(board)
    save_preview(frames,times,duration,out/'comparison.gif')

def export_project(manifest,view,action,out,mode="draft"):
    if view not in (*VIEWS,"all") or mode not in ("draft","reviewed-draft") or action not in ("walk","dash"):raise ValueError("Unknown export scope")
    if view=="all":
        if action!="walk":raise ValueError("All-view workflow supports walk; dash remains per-view")
        out=Path(out)
        if out.exists():raise ValueError("Export directory must be new")
        for v in VIEWS:preflight(manifest,v,action,mode)
        out.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.three-view-',dir=out.parent) as tmp:
            stage=Path(tmp)/'export'
            for v in VIEWS:export_project(manifest,v,action,stage/v,mode)
            comparison_preview(stage)
            write(stage/'summary.json',{'views':list(VIEWS),'action':action,'mode':mode,'draft':True,'approved':False})
            stage.rename(out)
        return
    from server import Handler,ThreadingHTTPServer
    p=Path(manifest);m=read(p)
    h,data=preflight(manifest,view,action,mode)
    data['action']=action
    if Path(out).exists():raise ValueError('Export directory must be new')
    # Reuse the exact browser API validation/export path; ephemeral loopback only.
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/render',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        result=json.load(urllib.request.urlopen(req))
    finally:server.shutdown();server.server_close()
    out=Path(out)
    if out.exists():raise ValueError('Export directory must be new')
    out.mkdir(parents=True);sheet=Image.open(io.BytesIO(base64.b64decode(result['sheet'].split(',',1)[1]))).convert('RGBA');sheet.save(out/'sheet.png');write(out/'animation.json',result['meta'])
    frames=[]
    for i,f in enumerate(result['meta']['frames']):
        r=f['rect'];im=sheet.crop((r['x'],r['y'],r['x']+r['w'],r['y']+r['h']));im.save(out/f'frame-{i:02}.png');frames.append(im)
    save_preview(frames,[f['time'] for f in result['meta']['frames']],result['meta']['duration'],out/'preview.gif')
    for name,color in [('black','#000000'),('cyan','#00ffff'),('magenta','#ff00ff'),('checker','#dddddd')]:
        proof=Image.new('RGBA',(384*len(frames),384),color)
        if name=='checker':
            from PIL import ImageDraw
            draw=ImageDraw.Draw(proof)
            for y in range(0,384,16):
                for x in range(0,proof.width,16):
                    if (x//16+y//16)%2:draw.rectangle((x,y,x+15,y+15),fill='#777777')
        for i,im in enumerate(frames):proof.alpha_composite(im,(384*i,0))
        proof.convert('RGB').save(out/f'qa-{name}.png')
    # The successful API request validated these same full-canvas layer bytes.
    from motion import cutouts,render
    def decode(encoded):return Image.open(io.BytesIO(base64.b64decode(encoded.split(',',1)[1]))).convert('RGBA')
    if data.get('demo'):
        from demo import demo
        _,_,layers=demo(view)
    else:
        layers=cutouts(decode(data['image']),data['rig'])
        layers.update({k:decode(v) for k,v in data.get('partImages',{}).items()})
        layers.update({'walk:'+k:decode(v) for k,v in data.get('walkPartImages',{}).items()})
    proof=Image.new('RGBA',(384*6,384*4),'#00ffff')
    for i in range(24):
        im,_=render(data['rig'],layers,action,i/24);im.save(out/f'intermediate-{i:02}.png');proof.alpha_composite(im,((i%6)*384,(i//6)*384))
    proof.convert('RGB').save(out/'qa-intermediate24-cyan.png')
    write(out/'review.json',{'draft':True,'approved':False,'view':view,'mode':mode,'action':action,'source_project_sha256':h,'human_evidence':m['views'][view]['review'].get(action,{}),'note':'Reinspect exported frames and intermediate phases; prior evidence is not automatic approval.'})

def preflight(manifest,view,action,mode):
    p=Path(manifest);m=read(p)
    if 'project' not in m:raise ValueError('No saved project bound; run workflow.py bind MANIFEST SAVED-PROJECT.json')
    sources_current(p,m);require_identity(m,p.parent)
    project=p.parent/m['project']['path'];h=digest(project)
    if h!=m['project']['sha256']:raise ValueError('Project changed; rebind and re-review')
    gates=GATES if mode=='reviewed-draft' else ('source_correspondence','proportions')
    for gate in gates:
        r=m['views'][view]['review'].get(action,{}).get(gate,{})
        if r.get('project_sha256')!=h or not evidence_current(r,p.parent):raise ValueError('Missing/stale evidence: '+view+'/'+gate)
    return h,read(project)['projects'][view]

def status(manifest):
    p=Path(manifest);m=read(p)
    def current(path,h):return path.is_file() and digest(path)==h
    source_ok=all(current(p.parent/r['input'],r['sha256']) for r in m['views'].values())
    project=m.get('project',{});project_ok=current(p.parent/project.get('path',''),project.get('sha256'))
    try:require_identity(m,p.parent);identity_ok=source_ok
    except ValueError:identity_ok=False
    m['integrity']={'sources_current':source_ok,'project_current':project_ok,'identity_current':identity_ok}
    for view,record in m['views'].items():
        record['export_scope']='manually registered draft; never automatic quality approval'
        record['status']='registered_needs_review' if project_ok else 'unbound_or_stale'
        record['missing_gates']={action:[g for g in GATES if not (source_ok and project_ok and identity_ok) or not evidence_current(record['review'].get(action,{}).get(g,{}),p.parent) or record['review'].get(action,{}).get(g,{}).get('project_sha256')!=project.get('sha256')] for action in ('walk','dash')}
    return m

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('init');q.add_argument('--out',required=True)
    for v in VIEWS:q.add_argument('--'+v,required=True)
    q=s.add_parser('identity');q.add_argument('manifest');q.add_argument('--evidence',required=True);q.add_argument('--note',required=True)
    q=s.add_parser('status');q.add_argument('manifest')
    q=s.add_parser('bind');q.add_argument('manifest');q.add_argument('project')
    q=s.add_parser('attest');q.add_argument('manifest');q.add_argument('--view',choices=VIEWS,default='side');q.add_argument('--action',choices=['walk','dash'],required=True);q.add_argument('--gate',choices=GATES,required=True);q.add_argument('--evidence',required=True);q.add_argument('--note',required=True)
    q=s.add_parser('export');q.add_argument('manifest');q.add_argument('--view',choices=(*VIEWS,'all'),default='side');q.add_argument('--mode',choices=['draft','reviewed-draft'],default='draft');q.add_argument('--action',choices=['walk','dash'],required=True);q.add_argument('--out',required=True)
    a=p.parse_args()
    try:
        if a.cmd=='init':print(json.dumps(init(a.out,{v:getattr(a,v) for v in VIEWS}),ensure_ascii=False,indent=2))
        elif a.cmd=='identity':identity(a.manifest,a.evidence,a.note)
        elif a.cmd=='status':print(json.dumps(status(a.manifest),ensure_ascii=False,indent=2))
        elif a.cmd=='bind':bind(a.manifest,a.project)
        elif a.cmd=='attest':attest(a.manifest,a.gate,a.evidence,a.note,a.action,a.view)
        else:export_project(a.manifest,a.view,a.action,a.out,a.mode)
    except (ValueError,KeyError,OSError,urllib.error.HTTPError) as e:p.exit(2,str(e)+'\n')
if __name__=='__main__':main()
