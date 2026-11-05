"""Continuous two-bone cutout mesh with interpolated rotation. Original implementation, no learned model.
A calibrated blend zone bends; source pixels are sampled, never invented.
"""
import math
import numpy as np
from PIL import Image

def _joint_mapper(rig,transforms,parent,child,radius=10,contour='rotation',ankle_depth=0,cloth_width=None,ankle_offset=0,cuff_normal=None):
    """Map registered source points using the same skinning as raster triangles."""
    a=rig['parts'][parent];b=rig['parts'][child]
    joint=np.array(b['start'],dtype=float);axis=np.array(b['end'],dtype=float)-joint;axis/=np.linalg.norm(axis)
    def rigid(p,name):
        part=rig['parts'][name];dest,theta=transforms[name];v=np.array(part['end'])-part['start'];angle=theta-math.atan2(v[1],v[0]);c=math.cos(angle);s=math.sin(angle)
        return np.array(dest)+np.array([[c,-s],[s,c]])@(p-part['start'])
    def limb_skin(p):
        q=max(0,min(1,(np.dot(p-joint,axis)+radius)/(2*radius)));w=q*q*(3-2*q)
        if cuff_normal:
            # Authored upright source band controls the entire cuff normal,
            # not the skeleton/centerline or new painted fabric.
            cw=max(0,min(1,(p[1]-cuff_normal['startY'])/(cuff_normal['endY']-cuff_normal['startY'])))
            w=max(w,cw*cw*(3-2*cw))
        # Interpolate rotation rather than matrices: avoids LBS candy-wrapper collapse.
        pa=rig['parts'][parent];ch=rig['parts'][child]
        ap=transforms[parent][1]-math.atan2(pa['end'][1]-pa['start'][1],pa['end'][0]-pa['start'][0])
        ac=transforms[child][1]-math.atan2(ch['end'][1]-ch['start'][1],ch['end'][0]-ch['start'][0])
        delta=(ac-ap+math.pi)%(2*math.pi)-math.pi;theta=ap+w*delta;c=math.cos(theta);sn=math.sin(theta)
        if contour=='centerline':
            # Keep upper/lower centerlines straight; blend only cross-section normals.
            # This is a contour correction, not a guarantee of area/volume preservation.
            u=float(np.dot(p-joint,axis));normal=np.array([-axis[1],axis[0]])
            v=float(np.dot(p-joint,normal));chosen=parent if u<0 else child
            center=rigid(joint+u*axis,chosen)
            return center+v*(np.array([[c,-sn],[sn,c]])@normal)
        return (1-w)*rigid(joint,parent)+w*rigid(joint,child)+np.array([[c,-sn],[sn,c]])@(p-joint)
    def skin(p):
        if cloth_width:
            # Geometric cloth-width calibration retains sampled outer ink lines.
            # A short transition below the cuff avoids a disconnected upper thigh.
            q=max(0,min(1,(cloth_width['fadeEnd']-p[1])/(cloth_width['fadeEnd']-cloth_width['fullUntil'])))
            w=q*q*(3-2*q);p=p.copy();p[0]=a['start'][0]+(p[0]-a['start'][0])*(1-(1-cloth_width['scale'])*w)
        moved=limb_skin(p)
        if parent.endswith('_thigh') and rig.get('waistAttachment'):
            hip=np.array(a['start'],dtype=float);thigh_axis=np.array(a['end'],dtype=float)-hip;thigh_length=np.linalg.norm(thigh_axis);thigh_axis/=thigh_length
            depth=np.dot(p-hip,thigh_axis)/thigh_length
            setting=rig['waistAttachment'];start=setting['startFraction'];end=setting['endFraction']
            q=max(0,min(1,(depth-start)/(end-start)));weight=q*q*(3-2*q)
            torso=rig['parts']['torso'];ta=transforms['torso'][1]-math.atan2(torso['end'][1]-torso['start'][1],torso['end'][0]-torso['start'][0])
            pa=transforms[parent][1]-math.atan2(a['end'][1]-a['start'][1],a['end'][0]-a['start'][0])
            correction=((ta-pa+math.pi)%(2*math.pi)-math.pi)*(1-weight);c=math.cos(correction);sn=math.sin(correction)
            hip_leg=rigid(hip,parent);hip_body=rigid(hip,'torso')
            moved=hip_leg+(1-weight)*(hip_body-hip_leg)+np.array([[c,-sn],[sn,c]])@(moved-hip_leg)
            # Preserve legacy short-circuit unless this source explicitly needs
            # both waist and distal shoe attachment in the same leg mesh.
            if not setting.get('ankleContinuity',False):return moved
        if ankle_depth and parent.endswith('_thigh'):
            # Distal sock/collar shares the rigid shoe transform. The shoe itself
            # is never warped; this removes divergent ownership at the ankle.
            footname=parent.replace('_thigh','_foot');ankle=np.array(b['end'],dtype=float)
            along=float(np.dot(p-ankle,axis));q=max(0,min(1,(along+ankle_depth)/(ankle_depth+2)));w=q*q*(3-2*q)
            fp=rig['parts'][footname];sp=rig['parts'][child]
            fa=transforms[footname][1]-math.atan2(fp['end'][1]-fp['start'][1],fp['end'][0]-fp['start'][0])
            sa=transforms[child][1]-math.atan2(sp['end'][1]-sp['start'][1],sp['end'][0]-sp['start'][0])
            delta=((fa-sa+math.pi)%(2*math.pi)-math.pi)*w
            c=math.cos(delta);sn=math.sin(delta);origin=np.array(transforms[footname][0])
            moved=origin+np.array([[c,-sn],[sn,c]])@(moved-origin)
            # Register distal sock artwork to the rigid shoe opening without
            # moving the skeleton or repainting its original outline.
            if ankle_offset:moved+=np.array([math.cos(fa),math.sin(fa)])*(ankle_offset*w)
        return moved
    return skin

def joint_mapper(rig,transforms,parent,child,*args,**kwargs):
    if not rig.get('_activeWalkProportions') or not parent.endswith('_thigh'):return _joint_mapper(rig,transforms,parent,child,*args,**kwargs)
    from proportions import source_point,widen_source
    from copy import deepcopy
    side=parent.split('_')[0];virtual=deepcopy(rig);virtual.pop('_activeWalkProportions',None)
    for name in (parent,child,side+'_foot'):
        for key in ('start','end'):virtual['parts'][name][key]=source_point(rig,side,rig['parts'][name][key]).tolist()
    mapped=_joint_mapper(virtual,transforms,parent,child,*args,**kwargs)
    return lambda p:mapped(source_point(rig,side,widen_source(rig,side,p)))

def draw_mapped(source,skin,step=6,diagnostics=None,grid_bounds=None):
    """Rasterize a source image through a supplied continuous point map."""
    box=grid_bounds or source.getbbox()
    if not box:return source.copy()
    pixels=np.asarray(source,dtype=float)/255;pixels[:,:,:3]*=pixels[:,:,3:4]
    out=np.zeros((384,384,4),dtype=float)
    x0,y0,x1,y1=box;xs=list(range(x0,x1,step))+[x1];ys=list(range(y0,y1,step))+[y1]
    vertices={(x,y):skin(np.array([x,y],dtype=float)) for y in ys for x in xs}
    if diagnostics is not None:diagnostics.update(invertedTriangles=0,minimumAreaRatio=1e9,maximumAreaRatio=0,activeInvertedTriangles=0,minimumActiveAreaRatio=1e9)
    for yi in range(len(ys)-1):
      for xi in range(len(xs)-1):
        quad=[(xs[xi],ys[yi]),(xs[xi+1],ys[yi]),(xs[xi+1],ys[yi+1]),(xs[xi],ys[yi+1])]
        for ids in [(0,1,2),(0,2,3)]:
          src=np.array([quad[k] for k in ids],dtype=float);dst=np.array([vertices[quad[k]] for k in ids]);matrix=np.column_stack((dst[1]-dst[0],dst[2]-dst[0]));det=np.linalg.det(matrix)
          if diagnostics is not None:
            refdet=np.linalg.det(np.column_stack((src[1]-src[0],src[2]-src[0])));ratio=det/refdet;diagnostics['invertedTriangles']+=int(ratio<=0);diagnostics['minimumAreaRatio']=min(diagnostics['minimumAreaRatio'],ratio);diagnostics['maximumAreaRatio']=max(diagnostics['maximumAreaRatio'],ratio)
            sx0,sy0=src.min(axis=0).astype(int);sx1,sy1=src.max(axis=0).astype(int)
            if pixels[sy0:sy1,sx0:sx1,3].max(initial=0)>.25:
                diagnostics['activeInvertedTriangles']+=int(ratio<=0);diagnostics['minimumActiveAreaRatio']=min(diagnostics['minimumActiveAreaRatio'],ratio)
          if abs(det)<1e-7:continue
          xmin=max(0,int(np.floor(dst[:,0].min())));xmax=min(384,int(np.ceil(dst[:,0].max())));ymin=max(0,int(np.floor(dst[:,1].min())));ymax=min(384,int(np.ceil(dst[:,1].max())))
          if xmin>=xmax or ymin>=ymax:continue
          yy,xx=np.mgrid[ymin:ymax,xmin:xmax];xy=np.stack([xx+.5,yy+.5],axis=-1);uv=(xy-dst[0])@np.linalg.inv(matrix).T;inside=(uv[:,:,0]>=-1e-8)&(uv[:,:,1]>=-1e-8)&(uv.sum(axis=2)<=1+1e-8)
          mapped=src[0]+uv[:,:,0,None]*(src[1]-src[0])+uv[:,:,1,None]*(src[2]-src[0]);sx=mapped[:,:,0]-.5;sy=mapped[:,:,1]-.5;ix=np.floor(sx).astype(int);iy=np.floor(sy).astype(int);fx=sx-ix;fy=sy-iy
          sample=np.zeros((*ix.shape,4))
          for dx,dy,weight in [(0,0,(1-fx)*(1-fy)),(1,0,fx*(1-fy)),(0,1,(1-fx)*fy),(1,1,fx*fy)]:sample+=pixels[np.clip(iy+dy,0,383),np.clip(ix+dx,0,383)]*weight[:,:,None]
          tile=out[ymin:ymax,xmin:xmax];tile[inside]=sample[inside]
    alpha=out[:,:,3:4];rgb=np.divide(out[:,:,:3],alpha,out=np.zeros_like(out[:,:,:3]),where=alpha>1e-8);return Image.fromarray(np.uint8(np.clip(np.concatenate([rgb,alpha],axis=2)*255,0,255)))

def draw_joint(rig,layers,transforms,parent,child,radius=10,step=6,diagnostics=None,contour='rotation',ankle_depth=0,cloth_width=None,ankle_offset=0,cuff_normal=None):
    if contour not in ('rotation','centerline'):raise ValueError('Unknown contour mode')
    a=rig['parts'][parent];b=rig['parts'][child]
    source=layers[parent].copy();source.alpha_composite(layers[child]);box=rig.get('_garmentMeshBounds',{}).get(parent,source.getbbox())
    if box is not None and (len(box)!=4 or any(not isinstance(v,int) for v in box) or not 0<=box[0]<box[2]<=384 or not 0<=box[1]<box[3]<=384):raise ValueError('Invalid internal mesh bounds')
    if not box:return source
    skin=joint_mapper(rig,transforms,parent,child,radius,contour,ankle_depth,cloth_width,ankle_offset,cuff_normal)
    return draw_mapped(source,skin,step,diagnostics,box)
