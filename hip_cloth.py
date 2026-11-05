"""Opt-in authored pelvis bridge and separate walk-only shorts leg openings.
No new artwork is synthesized here. Alternate cloth must be supplied and confirmed.
"""
import math
from copy import deepcopy
import numpy as np
from PIL import Image

SIZE=(384,384)
DEFAULTS=dict(capTop=-7,capEnd=17,feather=3,collarHalfWidth=7,collarFlare=.9,collarInset=-2,collarFade=5,bottomRotation=.5,rootOverlap=False)

def validate_attachment(rig):
    cfg=rig.get('hipAttachment')
    if cfg is None:return
    if not isinstance(cfg,dict) or cfg.get('mode')!='split-cloth':raise ValueError('Unknown hipAttachment')
    if rig.get('view')!='side' or rig.get('walkStyle')!='simple':raise ValueError('split-cloth needs side simple walk')
    if cfg.get('confirmed') is not True:raise ValueError('Confirm authored pelvis and walk cloth first')
    if set(cfg)-set(DEFAULTS)-{'mode','confirmed'}:raise ValueError('Unknown hip attachment calibration')
    if not isinstance(cfg.get('rootOverlap',False),bool):raise ValueError('rootOverlap must be boolean')
    ranges=dict(capTop=(-20,0),capEnd=(3,30),feather=(1,8),collarHalfWidth=(2,24),collarFlare=(.1,2),collarInset=(-10,10),collarFade=(1,10),bottomRotation=(0,.8))
    for key,(low,high) in ranges.items():
        v=cfg.get(key,DEFAULTS[key])
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not low<=v<=high:raise ValueError('Invalid hip calibration '+key)
    if cfg.get('capEnd',17)-cfg.get('capTop',-7)<=cfg.get('feather',3):raise ValueError('Hip cap bridge too short')
    meshes={(m['parent'],m['child']) for m in rig.get('jointMeshes',[])}
    if any((s+'_thigh',s+'_shin') not in meshes for s in ('left','right')):raise ValueError('split-cloth needs both thigh meshes')

def prepare(rig,layers,transforms,diagnostics=None):
    cfg={**DEFAULTS,**rig['hipAttachment']}
    for side in ('left','right'):
        im=layers.get('walk:'+side+'_thigh')
        if not isinstance(im,Image.Image) or im.size!=SIZE or im.mode!='RGBA' or im.getbbox() is None:raise ValueError('Missing confirmed walk cloth: '+side+'_thigh')
    rig=deepcopy(rig);rig.pop('waistAttachment',None);layers=dict(layers);transforms=dict(transforms)
    if cfg['rootOverlap']:
        # Shared waist overlap owns the garment root; no extra limb warp is added.
        # Explicitly supplied clean cap materials are required, not guessed at runtime.
        for side in ('left','right'):
            im=layers.get('walk:'+side+'_hip');base=layers[side+'_thigh']
            if not isinstance(im,Image.Image) or im.mode!='RGBA' or im.size!=SIZE or im.getbbox() is None:raise ValueError('Missing confirmed hip material: '+side)
            if im.getchannel('A').tobytes()!=base.getchannel('A').tobytes():raise ValueError('Hip material alpha must match original thigh')
    for name in rig.get('walkSkinShape',{}).get('bands',{}):
        if 'walk:'+name not in layers:raise ValueError('Missing confirmed skin variant: '+name)
    # Optional action-specific materials; silhouette changes need an explicit band gate.
    for name in ('left_shin','right_shin'):
        if 'walk:'+name in layers:
            im=layers['walk:'+name]
            if not isinstance(im,Image.Image) or im.mode!='RGBA' or im.size!=SIZE or im.getbbox() is None:raise ValueError('Invalid walk shin material: '+name)
            # Material-only override must not silently alter the silhouette.
            from skin_shape import check_variant
            check_variant(rig,name,layers[name],im)
            layers[name]=im
    from ownership import apply_ownership
    layers=apply_ownership(rig,layers)
    pelvis=Image.new('RGBA',SIZE)
    def map_point(point,name):
        p=rig['parts'][name];dest,theta=transforms[name];angle=theta-math.atan2(p['end'][1]-p['start'][1],p['end'][0]-p['start'][0]);c=math.cos(angle);sn=math.sin(angle)
        return np.array(dest)+np.array([[c,-sn],[sn,c]])@(np.array(point)-p['start'])
    for side in ('left','right'):
        name=side+'_thigh';source=layers['walk:'+side+'_hip'] if cfg['rootOverlap'] else layers[name];part=rig['parts'][name];hip=part['start'];yy=np.arange(384)[:,None]
        capmask=np.broadcast_to(np.clip((hip[1]+cfg['capEnd']-yy)/cfg['feather'],0,1),SIZE)
        cap=source.copy();cap.putalpha(Image.fromarray(np.uint8(np.asarray(source.getchannel('A'))*capmask)))
        torso=rig['parts']['torso'];box=source.getbbox();x0,x1=box[0],box[2];y0,y1=hip[1]+cfg['capTop'],hip[1]+cfg['capEnd']
        src=np.array([[x0,y0],[x1,y0],[x1,y1],[x0,y1]],float)
        torsoangle=transforms['torso'][1]-math.atan2(torso['end'][1]-torso['start'][1],torso['end'][0]-torso['start'][0]);legangle=transforms[name][1]-math.atan2(part['end'][1]-part['start'][1],part['end'][0]-part['start'][0])
        theta=torsoangle+cfg['bottomRotation']*((legangle-torsoangle+math.pi)%(2*math.pi)-math.pi);c=math.cos(theta);sn=math.sin(theta);lowercenter=map_point([hip[0],y1],name)
        cloth_scale=next((m.get('walkClothWidth',{}).get('scale',1) for m in rig.get('jointMeshes',[]) if m['parent']==name),1)
        dst=np.array([map_point(src[0],'torso'),map_point(src[1],'torso'),lowercenter+np.array([c*(x1-hip[0]),sn*(x1-hip[0])])*cloth_scale,lowercenter+np.array([c*(x0-hip[0]),sn*(x0-hip[0])])*cloth_scale])
        edges=np.roll(dst,-1,axis=0)-dst;nextedges=np.roll(edges,-1,axis=0);cross=edges[:,0]*nextedges[:,1]-edges[:,1]*nextedges[:,0]
        area=.5*abs(np.sum(dst[:,0]*np.roll(dst[:,1],-1)-dst[:,1]*np.roll(dst[:,0],-1)));ratio=area/((x1-x0)*(y1-y0))
        if not np.isfinite(dst).all() or min(cross)<=1e-5 or ratio<.05:raise ValueError('Pelvis bridge folds or collapses: '+side)
        if diagnostics is not None:diagnostics.append(dict(side=side,areaRatio=float(ratio),minCornerCross=float(min(cross)),sourceQuad=src.tolist(),destinationQuad=dst.tolist()))
        A=[];b=[]
        for (x,y),(u,v) in zip(dst,src):
            A.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);b.extend([u,v])
        coeff=np.linalg.solve(np.array(A),np.array(b));cap=cap.transform(SIZE,Image.Transform.PERSPECTIVE,coeff,Image.Resampling.BICUBIC);pelvis.alpha_composite(cap)
        xx=np.arange(384)[None,:];depth=yy-hip[1];halfwidth=cfg['collarHalfWidth']+np.maximum(depth,0)*cfg['collarFlare']
        legmask=np.clip((depth-cfg['collarInset'])/cfg['collarFade'],0,1)*np.clip((halfwidth-np.abs(xx-hip[0]))/3,0,1)
        source=layers['walk:'+name];leg=source.copy();leg.putalpha(Image.fromarray(np.uint8(np.asarray(source.getchannel('A'))*legmask)));layers[name]=leg
    # Temporary draw-only part; saved skeleton remains the original12 parts.
    rig['parts']['pelvis']={'start':[0,0],'end':[0,1]};layers['pelvis']=pelvis;transforms['pelvis']=([0,0],math.pi/2)
    rig['order']=list(rig['order']);index=rig['order'].index('right_thigh')+1 if cfg['rootOverlap'] else rig['order'].index('left_thigh');rig['order'].insert(index,'pelvis')
    if rig.get('walkGarment'):
        from garment import apply_garment
        layers=apply_garment(rig,layers,transforms,diagnostics)
    return rig,layers,transforms
