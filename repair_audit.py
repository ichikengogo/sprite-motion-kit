"""Read-only pixel invariants for a localized sprite repair, not an art judge."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image


def frames(root):
    found=sorted(Path(root).glob('frame-*.png'))
    if not found: raise ValueError('No frame-*.png files')
    return found


def gif_timing(path):
    with Image.open(path) as im:
        if im.format!='GIF': raise ValueError('Timing evidence must be GIF')
        result=[];loop=im.info.get('loop')
        for i in range(im.n_frames):
            im.seek(i);result.append(im.info.get('duration',0))
        if any(x<=0 for x in result): raise ValueError('Missing positive GIF duration')
        return {'durationsMs':result,'loop':loop}


def audit(before, after, allowed_masks, before_gif=None, after_gif=None):
    """Mask L>0 is allowed edit region. One mask per named frame, no auto-registration."""
    old,new=frames(before),frames(after)
    if [p.name for p in old]!=[p.name for p in new]: raise ValueError('Frame names/count/order differ')
    if bool(before_gif)!=bool(after_gif): raise ValueError('Both timing files required')
    rows=[]
    for a,b in zip(old,new):
        m=Path(allowed_masks)/a.name
        if not m.is_file(): raise ValueError('Missing explicit allowed mask: '+a.name)
        with Image.open(a) as im: aa=np.array(im.convert('RGBA'))
        with Image.open(b) as im: bb=np.array(im.convert('RGBA'))
        with Image.open(m) as im:
            if im.mode not in ('1','L'): raise ValueError('Use grayscale L masks; nonzero explicitly allows changes')
            mask=np.array(im.convert('L'))>0
        if aa.shape!=bb.shape or mask.shape!=aa.shape[:2]: raise ValueError('Frame/mask dimensions differ')
        changed=np.any(aa!=bb,axis=2);yy,xx=np.where(changed)
        rows.append({'frame':a.name,'changedPixels':int(changed.sum()),'outsideAllowedPixels':int((changed&~mask).sum()),
          'allowedFraction':float(mask.mean()),'changedBounds':None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],
          'beforeSHA256':hashlib.sha256(a.read_bytes()).hexdigest(),'afterSHA256':hashlib.sha256(b.read_bytes()).hexdigest(),
          'maskSHA256':hashlib.sha256(m.read_bytes()).hexdigest()})
    timing=None
    if before_gif:
        x,y=gif_timing(before_gif),gif_timing(after_gif)
        timing={'beforeMs':x['durationsMs'],'afterMs':y['durationsMs'],'beforeLoop':x['loop'],'afterLoop':y['loop'],'equal':x==y,'frameCountMatchesPNG':len(x['durationsMs'])==len(y['durationsMs'])==len(rows)}
    exact=all(r['outsideAllowedPixels']==0 for r in rows)
    return {'schema':'localized-repair-audit/1','frames':rows,'outsideAllowedExact':exact,'timing':timing,
      'invariantsPass':exact and (timing is None or (timing['equal'] and timing['frameCountMatchesPNG'])),
      'visualApproval':False,'limitations':['Masks are authored claims: inspect their scope; all-white masks prove nothing about preservation.',
      'Pixel equality outside a region does not prove anatomy, palm orientation, cloth preservation, contact or natural motion.',
      'No alignment, scale fitting or tolerance is applied; genuine whole-body motion changes will be detected unless explicitly allowed.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('before','after','allowed-masks','out'):p.add_argument('--'+k,required=True)
    p.add_argument('--before-gif');p.add_argument('--after-gif');a=p.parse_args()
    result=audit(a.before,a.after,a.allowed_masks,a.before_gif,a.after_gif)
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['invariantsPass'] else 2
if __name__=='__main__':raise SystemExit(main())
