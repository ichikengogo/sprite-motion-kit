"""Explicitly low-confidence geometric initialization; no anatomical inference."""
import math
from PIL import Image,ImageDraw
from demo import demo
from motion import SIZE,validate
COMMANDS={'歩行':'walk','歩く':'walk','walk':'walk','ダッシュ':'dash','走る':'dash','run':'dash','dash':'dash'}
def parse_command(text):
    if not isinstance(text,str) or len(text)>80:raise ValueError('Command must be one supported word')
    value=COMMANDS.get(text.strip().lower())
    if not value:raise ValueError('対応する指示: 歩行 / 歩く / walk / ダッシュ / 走る / run / dash（単語のみ）')
    return value

def suggest(image,view,facing="right"):
    if facing not in ("left","right"):raise ValueError("Unknown facing")
    if view not in ('front','side','back'):raise ValueError('Unknown view')
    if image.size!=SIZE or image.mode!='RGBA':raise ValueError('Expected 384x384 RGBA PNG')
    alpha=image.getchannel('A');silhouette=alpha.point(lambda v:255 if v>=32 else 0);bounds=silhouette.getbbox()
    if not bounds:raise ValueError('No visible silhouette (alpha >=32)')
    if alpha.getextrema()[0]==255:raise ValueError('Transparent background required')
    x0,y0,x1,y1=bounds;w=x1-x0;h=y1-y0
    if w<24 or h<72:raise ValueError('Silhouette too small for reliable initialization; need width>=24, height>=72')
    if w/h>.90 or w/h<.12:raise ValueError('Unsupported silhouette aspect ratio for upright humanoid template; use manual editor')
    source,rig,_=demo(view);sx0,sy0,sx1,sy1=source.getbbox()
    def fit(p):return [round(x0+((sx1-p[0]) if view=='side' and facing=='left' else (p[0]-sx0))*w/(sx1-sx0),3),round(y0+(p[1]-sy0)*h/(sy1-sy0),3)]
    rig['facing']=facing;rig['root']=fit(rig['root']);rig['confirmed']=False;rig['origin']='unconfirmed geometric alpha-bounds template'
    masks={};occupancy={}
    for name,part in rig['parts'].items():
        part['start']=fit(part['start']);part['end']=fit(part['end']);part['polygon']=[fit(p) for p in part['polygon']];part['confirmed']=False;part['availability']='unverified'
        mask=Image.new('1',SIZE);ImageDraw.Draw(mask).polygon([tuple(p) for p in part['polygon']],fill=1);masks[name]=mask
        area=sum(mask.getdata());visible=sum(1 for m,a in zip(mask.getdata(),silhouette.getdata()) if m and a)
        occupancy[name]={'visiblePixels':visible,'maskPixels':area,'visibleFraction':round(visible/max(1,area),3),'confidence':'low','hiddenArtwork':'unverified'}
    visible_indices=[i for i,a in enumerate(silhouette.getdata()) if a];counts=[0]*(384*384)
    for mask in masks.values():
        for i,m in enumerate(mask.getdata()):counts[i]+=int(m)
    overlapping=sum(counts[i]>1 for i in visible_indices);uncovered=sum(counts[i]==0 for i in visible_indices)
    warning=['幾何学的な候補です。人体・服・関節を認識していません。','全12パーツの手動確認が必要です。隠れた面は未検証・未生成です。']
    empty=[name for name,v in occupancy.items() if not v['visiblePixels']]
    if empty:warning.append('可視画素のない部品: '+', '.join(empty))
    if overlapping:warning.append(f'{overlapping}可視画素が複数マスクに重複。重なった絵の分離はできません。')
    if uncovered:warning.append(f'{uncovered}可視画素が未割当。髪・服・装飾の欠落を確認してください。')
    if view=='side':warning.append('横向きでは奥側の腕・脚が隠れる場合があります。左右候補を別の実在部品とみなさないでください。')
    if w/h>.65:warning.append('横幅が広いシルエットです。腕/服により候補が大きく外れる可能性があります。')
    report={'method':'alpha-bounds + fixed upright template; NOT learned segmentation','confidence':'low','bounds':list(bounds),'overlapVisiblePixels':overlapping,'uncoveredVisiblePixels':uncovered,'emptyParts':empty,'parts':occupancy,'warnings':warning}
    rig['suggestion']=report;validate(rig,image);return rig,report
