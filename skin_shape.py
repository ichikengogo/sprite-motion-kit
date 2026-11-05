"""Explicit walk-only authored shin silhouette replacement inside a confirmed row band.
No pixels are generated here; the supplied variant owns the allowed band.
"""
import numpy as np

def validate_skin_shape(rig):
    cfg=rig.get('walkSkinShape')
    if cfg is None:return
    if not isinstance(cfg,dict) or set(cfg)!={'confirmed','bands'} or cfg['confirmed'] is not True:raise ValueError('Confirm walk skin shape first')
    if rig.get('view')!='side' or rig.get('walkStyle')!='simple' or not rig.get('hipAttachment'):raise ValueError('Walk skin shape requires side simple split-cloth')
    bands=cfg['bands']
    if not isinstance(bands,dict) or not bands or set(bands)-{'left_shin','right_shin'}:raise ValueError('Skin bands require left/right shin')
    for name,band in bands.items():
        if not isinstance(band,list) or len(band)!=2 or any(isinstance(v,bool) or not isinstance(v,int) for v in band):raise ValueError('Skin band needs two integer rows')
        top,bottom=band
        if not 0<=top<bottom<=384 or bottom-top>64:raise ValueError('Invalid skin band')
        # Must stop above the manually registered ankle; do not replace shoes.
        if bottom>rig['parts'][name]['end'][1]:raise ValueError('Skin band reaches beyond ankle')

def check_variant(rig,name,base,variant):
    band=rig.get('walkSkinShape',{}).get('bands',{}).get(name)
    if band is None:
        if variant.getchannel('A').tobytes()!=base.getchannel('A').tobytes():raise ValueError('Walk shin material alpha must match original')
        return
    top,bottom=band;a=np.asarray(base);b=np.asarray(variant)
    if not np.array_equal(a[:top],b[:top]) or not np.array_equal(a[bottom:],b[bottom:]):raise ValueError('Skin variant changes pixels outside confirmed band')
    if not b[top:bottom,:,3].max(initial=0):raise ValueError('Skin variant band is empty')
