"""Confirmed source-space keep polygons for walk-only leg ownership.

This is cutout segmentation, not RGB repair or hidden anatomy synthesis.
Original layers are retained; alpha can only decrease.
"""
import math
from PIL import Image,ImageDraw,ImageChops

PARTS={'left_thigh','right_thigh','left_shin','right_shin'}

def validate_ownership(rig):
    config=rig.get('walkOwnership')
    if config is None:return
    if not isinstance(config,dict) or set(config)!={'confirmed','keepPolygons'} or config['confirmed'] is not True:raise ValueError('Confirm source ownership masks first')
    if rig.get('view')!='side' or rig.get('walkStyle')!='simple' or not rig.get('hipAttachment'):raise ValueError('Ownership masks need side simple split-cloth walk')
    polygons=config['keepPolygons']
    if not isinstance(polygons,dict) or not 1<=len(polygons)<=4 or set(polygons)-PARTS:raise ValueError('Invalid ownership part selection')
    for polygon in polygons.values():
        if not isinstance(polygon,list) or not 3<=len(polygon)<=64:raise ValueError('Ownership polygon needs3..64 points')
        for point in polygon:
            if not isinstance(point,list) or len(point)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=384 for v in point):raise ValueError('Invalid ownership point')
        area=abs(sum(polygon[i][0]*polygon[(i+1)%len(polygon)][1]-polygon[(i+1)%len(polygon)][0]*polygon[i][1] for i in range(len(polygon))))/2
        if area<.5:raise ValueError('Degenerate ownership polygon')

def apply_ownership(rig,layers):
    validate_ownership(rig)
    if not rig.get('walkOwnership'):return layers
    result=dict(layers)
    for name,polygon in rig['walkOwnership']['keepPolygons'].items():
        key='walk:'+name if name.endswith('_thigh') else name
        source=layers[key]
        mask=Image.new('L',(1536,1536));ImageDraw.Draw(mask).polygon([(round(x*4),round(y*4)) for x,y in polygon],fill=255)
        mask=mask.resize((384,384),Image.Resampling.LANCZOS)
        output=source.copy();output.putalpha(ImageChops.multiply(source.getchannel('A'),mask))
        if output.getbbox() is None:raise ValueError('Ownership mask removes entire part: '+name)
        result[key]=output
    return result
