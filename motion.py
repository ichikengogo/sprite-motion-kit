"""Original cutout prototype with optional local two-bone joint meshes. No learned model or network."""
import math
from PIL import Image, ImageDraw

SIZE = (384, 384)
PARTS = ['torso','head'] + [f'{s}_{p}' for s in ('left','right') for p in ('upper_arm','forearm','thigh','shin','foot')]
def add(a,b): return [a[0]+b[0],a[1]+b[1]]
def sub(a,b): return [a[0]-b[0],a[1]-b[1]]
def length(v): return math.hypot(*v)
def angle(v): return math.atan2(v[1],v[0])
def rotate(v,a): return [v[0]*math.cos(a)-v[1]*math.sin(a),v[0]*math.sin(a)+v[1]*math.cos(a)]
def mix(a,b,t): return a+(b-a)*t

def ik(hip, target, a, b, bend=1):
    v=sub(target,hip); requested=length(v); d=max(abs(a-b)+1e-5,min(a+b-1e-5,requested))
    theta=angle(v); alpha=math.acos(max(-1,min(1,(a*a+d*d-b*b)/(2*a*d))))
    knee=add(hip,rotate([a,0],theta+bend*alpha))
    ankle=add(hip,rotate([d,0],theta))
    return knee,ankle,abs(requested-d)

def template(action):
    if action=='walk': return dict(duration=1.0,stance=.62,stride=56,lift=19,bob=2,lean=.025,arm=.35)
    if action=='dash': return dict(duration=.64,stance=.38,stride=86,lift=40,bob=7,lean=.14,arm=.85)
    raise ValueError('action must be walk or dash')

def gait_config(rig,action):
    cfg=template(action).copy()
    if rig.get('gaitProfile') in ('evidence-v1','coupled-v2'):
        cfg.update(stance=.60 if action=='walk' else .34,lift=19 if action=='walk' else 60,lean=.025 if action=='walk' else .12)
    if rig.get('gaitProfile')=='coupled-v2':cfg.update(lean=.035 if action=='walk' else .16,arm=.6 if action=='walk' else 1.15,lift=19 if action=='walk' else 52)
    if action=='walk' and rig.get('walkStyle')=='purposeful':cfg.update(stance=.60,stride=100,lift=10,bob=1.3,lean=.04)
    if action=='walk' and rig.get('walkStyle')=='wide-stable':cfg.update(stance=.60,stride=132,lift=22,bob=1.3,lean=.04)
    if action=='walk' and rig.get('walkStyle')=='simple':cfg.update(stance=.60,stride=170,lift=48,bob=2.5,lean=.025)
    if action=='walk' and rig.get('walkStyle')=='simple' and rig.get('walkPosture')=='upright':cfg['stride']=160
    return cfg

def smooth(t):return t*t*(3-2*t)

def limit_recovery_bend(bend, maximum=75):
    """Smooth knee-fold cap; preserve bends below maximum minus10 degrees."""
    start=math.radians(maximum-10);end=math.radians(maximum+10)
    if abs(bend)<=start:return bend
    q=min(1,(abs(bend)-start)/(end-start))
    return math.copysign(start+math.radians(10)*(2*q-q*q),bend)

def foot_path(rig,side,index,phase,cfg,action):
    parts=rig['parts'];direction=-1 if rig['view']=='side' and rig.get('facing','right')=='left' else 1
    scale=rig.get('motionScale',1.0);ph=(phase+index*.5)%1;stance=ph<cfg['stance'];stride=cfg['stride']*scale*(1 if rig['view']=='side' else .20)
    evidence=rig.get('gaitProfile') in ('evidence-v1','coupled-v2') or (action=='walk' and rig.get('walkStyle') in ('purposeful','wide-stable','simple'));foot=parts[side+'_foot'];neutral=parts[side+'_shin']['end'];roll=0.0;mode='flat' if stance else 'air'
    markers=all(k in foot for k in ('forefootContact','heelContact'))
    toe_vector=sub(foot.get('forefootContact',foot['start']),foot['start']);heel_vector=sub(foot.get('heelContact',foot['start']),foot['start'])
    purposeful=action=='walk' and rig.get('walkStyle') in ('purposeful','wide-stable','simple')
    toe_roll=(.18 if purposeful else .24) if action=='walk' else .34;heel_roll=(.06 if purposeful else .10) if action=='walk' else 0
    if action=='walk' and rig.get('walkStyle') in ('wide-stable','simple'):
        # Calibrate toe-up relative to the artwork's own projected sole slope.
        sole_slope=math.atan2(toe_vector[1]-heel_vector[1],max(1,abs(toe_vector[0]-heel_vector[0]))) if markers else 0
        heel_roll=max(.08,min(.35,.16+sole_slope))
    toe_offset=sub(toe_vector,rotate(toe_vector,direction*toe_roll));heel_offset=sub(heel_vector,rotate(heel_vector,-direction*heel_roll))
    offset=[0,0];anchor_vector=[0,0]
    if stance:
        dx=mix(stride/2,-stride/2,ph/cfg['stance']);lift=0
        if evidence and markers:
            start=.35 if action=='walk' else cfg['stance']*.6
            if action=='walk' and ph<.10:
                mode='heel';roll=-direction*heel_roll*(1-smooth(ph/.10));anchor_vector=heel_vector
            elif ph>=start:
                mode='toe';roll=direction*toe_roll*smooth((ph-start)/(cfg['stance']-start));anchor_vector=toe_vector
            offset=sub(anchor_vector,rotate(anchor_vector,roll))
    else:
        q=(ph-cfg['stance'])/(1-cfg['stance'])
        if action=='walk' and rig.get('walkStyle')=='simple' and rig.get('legSwing')=='thigh-led':q=q+.15*math.sin(math.pi*q)
        u=smooth(q)
        if evidence:
            # Hermite end tangents match stance retreat; includes terminal retraction.
            m=-stride*(1-cfg['stance'])/cfg['stance']
            dx=mix(-stride/2,stride/2,smooth(q)) if action=='walk' and rig.get('walkStyle')=='simple' else (2*q**3-3*q*q+1)*(-stride/2)+(q**3-2*q*q+q)*m+(-2*q**3+3*q*q)*(stride/2)+(q**3-q*q)*m
            peak=(.5 if rig.get('walkStyle')=='simple' else .35) if action=='walk' else .30;v=q/peak if q<=peak else (1-q)/(1-peak)
            lift=cfg['lift']*scale*math.sin(math.pi/2*v)**2
            if markers:
                roll=direction*(toe_roll*(1-u)-heel_roll*u);offset=[mix(toe_offset[j],heel_offset[j],u) for j in range(2)]
                if action=='walk' and rig.get('walkStyle') in ('wide-stable','simple'):
                    # Unload trailing toe, then dorsiflex for clearance; settle to heel strike.
                    if q<.35: swing_pitch=mix(toe_roll,-(heel_roll+.02),smooth(q/.35))
                    else: swing_pitch=mix(-(heel_roll+.02),-heel_roll,smooth((q-.35)/.65))
                    roll=direction*swing_pitch
        else:dx=mix(-stride/2,stride/2,u);lift=cfg['lift']*scale*math.sin(math.pi*q)**2
    gait_center=sum(parts[s+'_shin']['end'][0] for s in ('left','right'))/2 if action=='walk' and rig.get('walkStyle')=='simple' else neutral[0]
    if action=='walk' and rig.get('walkStyle')=='simple' and rig.get('walkHipDrive',{}).get('gaitCenter')=='source-ankles':
        # Retain authored side-view depth/parallax instead of forcing both feet
        # onto a shared ankle axis. Stride velocity and source hips stay unchanged.
        gait_center=neutral[0]
    target=add([gait_center+dx*direction,neutral[1]-lift],offset)
    # Optional calibrated alpha hull: support the whole rigid shoe, not only a pivot.
    # Y correction follows the rotating sole envelope; it is rolling, not a fixed marker.
    outline=foot.get('soleOutline',[])
    if evidence and outline:
        if not stance:
            floor,edge=(2,.12) if action=='walk' and rig.get('walkStyle') in ('wide-stable','simple') else (4,.07)
            lift=max(lift,floor*smooth(min(q/edge,(1-q)/edge,1)))
        original_bottom=max(p[1] for p in outline)
        rotated_bottom=max(rotate(sub(p,foot['start']),roll)[1] for p in outline)
        target[1]=original_bottom-rotated_bottom-lift

    contact_point=add(target,rotate(anchor_vector,roll))
    return dict(phase=ph,contact=stance,target=target,roll=roll,contactMode=mode,contactPoint=contact_point,ground_velocity=direction*stride/(cfg['stance']*cfg['duration']))

def pose(rig,action,t):
    simple=action=='walk' and rig.get('walkStyle')=='simple'
    upright=simple and rig.get('walkPosture')=='upright'
    thigh_led=simple and rig.get('legSwing')=='thigh-led'
    separated=thigh_led and rig.get('legRecovery')=='clear-step'
    wide_stable=action=='walk' and rig.get('walkStyle') in ('wide-stable','simple')
    purposeful=action=='walk' and rig.get('walkStyle') in ('purposeful','wide-stable','simple')
    if purposeful:rig={**rig,'gaitProfile':'coupled-v2','preserveReach':True}
    cfg=gait_config(rig,action);phase=t%1;parts=rig['parts'];root=rig['root'];side=rig['view']=='side'
    scale=rig.get('motionScale',1.0);direction=-1 if side and rig.get('facing','right')=='left' else 1
    hip_drive=rig.get('walkHipDrive') if simple else None
    if rig.get('gaitProfile') in ('evidence-v1','coupled-v2'):
        wave=math.cos(4*math.pi*(phase-cfg['stance']/2))
        vertical=-cfg['bob']*scale*(1+wave)/2 if action=='walk' else cfg['bob']*scale*wave
    else:vertical=-cfg['bob']*scale*(1-math.cos(phase*4*math.pi))/2
    if simple:
        # Authored body levels, not a measured biomechanical center of mass.
        key=(phase*8)%4;index=int(key);levels=[0,2,-1,-2,0] if upright else [9,11,4,2,9]
        vertical=mix(levels[index],levels[index+1],smooth(key-index))
    lean=cfg['lean']*direction if side else 0
    coupled=rig.get('gaitProfile')=='coupled-v2'
    if coupled and not wide_stable:lean+=.018*math.sin(4*math.pi*phase)*direction
    base=add(root,[0,rig.get('pelvisDrop',0)+vertical]);out={};diagnostics=[]
    torso_lean=lean+(.025*math.sin(2*math.pi*phase) if coupled and not wide_stable else 0)
    hip_lean=lean-(.020*math.sin(2*math.pi*phase) if coupled and not wide_stable else 0)
    if hip_drive:
        # Authored pelvis load-transfer and restrained torso counter-motion.
        # Source hips, stance foot targets and bone lengths are not rescaled.
        base[0]+=direction*hip_drive['pelvisShift']*math.sin(4*math.pi*phase)
        hip_lean+=direction*hip_drive['pelvisTilt']*math.sin(2*math.pi*phase)
        torso_lean-=direction*hip_drive['torsoCounter']*math.sin(2*math.pi*phase)
    def bodypoint(p,torso=False):
        # Deliberate side-view depth simplification for equal readable steps.
        if simple and rig.get('walkHipRegistration','legacy-centered')!='source' and any(p==parts[s+'_thigh']['start'] for s in ('left','right')):
            p=[sum(parts[s+'_thigh']['start'][0] for s in ('left','right'))/2,p[1]]
        return add(base,rotate(sub(p,root),torso_lean if torso else hip_lean))
    paths={s:foot_path(rig,s,i,phase,cfg,action) for i,s in enumerate(('left','right'))};support=0.0
    if rig.get('preserveReach',False):
        for s,path in paths.items():
            thigh=parts[s+'_thigh'];shin=parts[s+'_shin'];hip=bodypoint(thigh['start']);target=path['target']
            reach=length(sub(thigh['end'],thigh['start']))+length(sub(shin['end'],shin['start']))-1e-4
            if purposeful:reach-=.15+.15*math.cos(2*math.pi*path['phase'])**2
            dx=abs(target[0]-hip[0])
            if dx<reach:support=max(support,target[1]-math.sqrt(reach*reach-dx*dx)-hip[1])
        if wide_stable and (not simple or upright):
            # Smooth upper envelope of required root lowering. Includes current constraints,
            # so planted/swing targets remain reachable; no foot shift or bone scaling.
            requirements=[0.0]
            for sample in range(-60,61):
                dt=sample*.002
                penalty=.6*(dt/.04)**2
                for index,side_name in enumerate(('left','right')):
                    path=foot_path(rig,side_name,index,phase+dt,cfg,action);thigh=parts[side_name+'_thigh'];shin=parts[side_name+'_shin'];hip=bodypoint(thigh['start']);target=path['target']
                    reach=length(sub(thigh['end'],thigh['start']))+length(sub(shin['end'],shin['start']))-1e-4-.15-.15*math.cos(2*math.pi*path['phase'])**2;dx=abs(target[0]-hip[0])
                    if dx<reach:requirements.append(target[1]-math.sqrt(reach*reach-dx*dx)-hip[1]-penalty)
            maximum=max(requirements);support=maximum+.10*math.log(sum(math.exp((value-maximum)/.10) for value in requirements))
        base[1]+=max(0,support)
    for name in ('torso','head'):
        p=parts[name];out[name]=(bodypoint(p['start'],True),angle(sub(p['end'],p['start']))+torso_lean)
    for s,path in paths.items():
        leg=parts[s+'_thigh'];shin=parts[s+'_shin'];foot=parts[s+'_foot'];hip=bodypoint(leg['start']);a=length(sub(leg['end'],leg['start']));b=length(sub(shin['end'],shin['start']))
        knee,ankle,clamp=ik(hip,path['target'],a,b,-direction if side else (1 if s=='left' else -1))
        recovery_shift=0.0
        if thigh_led and not path['contact']:
            # Hybrid swing: retain recovered thigh, unfold shin with fixed bone length.
            thigh_angle=angle(sub(knee,hip));shin_angle=angle(sub(ankle,knee))
            bend=(shin_angle-thigh_angle+math.pi)%(2*math.pi)-math.pi;limited=limit_recovery_bend(bend,55 if separated else 75)
            if separated:
                recovery=(path['phase']-cfg['stance'])/(1-cfg['stance'])
                edge=smooth(max(0,min(1,recovery/.15,(1-recovery)/.15)))
                limited=mix(bend,limited,edge)
            if abs(limited-bend)>1e-12:
                old_ankle=ankle
                if separated:
                    # A readable swing silhouette, not a material/alpha trick: unfold the
                    # calf and advance its thigh slightly while leaving support untouched.
                    recovery=(path['phase']-cfg['stance'])/(1-cfg['stance'])
                    weight=smooth(min(1,(abs(bend)-abs(limited))/math.radians(20)))
                    thigh_angle-=direction*math.radians(8)*math.sin(math.pi*recovery)**2*weight
                    knee=add(hip,rotate([a,0],thigh_angle))
                ankle=add(knee,rotate([b,0],thigh_angle+limited))
                shift=sub(ankle,old_ankle);recovery_shift=length(shift)
                path={**path,'target':ankle,'contactPoint':add(path['contactPoint'],shift)}
        hip_swing_angle=0.0
        if hip_drive and not path['contact']:
            # Initiate the whole recovered leg at its hip, not an independent calf kick.
            # sin² rejoins the authored stance path with zero angular velocity at ends.
            recovery=(path['phase']-cfg['stance'])/(1-cfg['stance'])
            hip_swing_angle=-direction*hip_drive['swingLead']*math.sin(math.pi*recovery)**2
            old_ankle=ankle
            knee=add(hip,rotate(sub(knee,hip),hip_swing_angle))
            ankle=add(hip,rotate(sub(ankle,hip),hip_swing_angle))
            shift=sub(ankle,old_ankle);recovery_shift+=length(shift)
            path={**path,'target':ankle,'contactPoint':add(path['contactPoint'],shift)}
        out[s+'_thigh']=(hip,angle(sub(knee,hip)));out[s+'_shin']=(knee,angle(sub(ankle,knee)));out[s+'_foot']=(ankle,angle(sub(foot['end'],foot['start']))+path['roll'])
        cp=add(path['contactPoint'],sub(ankle,path['target']))
        diagnostics.append(dict(side=s,contact=path['contact'],target=path['target'],ankle=ankle,contactPoint=cp,contactMode=path['contactMode'],footRollRadians=path['roll'],reach_error=clamp,hip=hip,knee=knee,lengths=[a,b],supportCorrectionPx=max(0,support),ground_velocity=path['ground_velocity']))
        if thigh_led:diagnostics[-1].update(legSwing='thigh-led',recoveryFootAdjustmentPx=recovery_shift)
        if hip_drive:diagnostics[-1].update(walkHipDrive=True,hipSwingLeadRadians=hip_swing_angle,pelvisLeanRadians=hip_lean,torsoLeanRadians=torso_lean)
        upper=parts[s+'_upper_arm'];fore=parts[s+'_forearm'];shoulder=bodypoint(upper['start'],True);ph=path['phase']
        if action=='walk' and rig.get('armPose')=='held-source':
            # Opt-in source pose for hands gripping straps or another torso-fixed item.
            # Preserve the authored bent arms; zero swing alone still points arms down.
            for name in (s+'_upper_arm',s+'_forearm'):
                part=parts[name]
                out[name]=(bodypoint(part['start'],True),angle(sub(part['end'],part['start']))+torso_lean)
            diagnostics[-1].update(armPose='held-source',armReachErrorPx=0,
                                  shoulder=shoulder,wrist=bodypoint(fore['end'],True))
            continue
        swing=cfg['arm']*rig.get('armSwingScale',1)*math.cos(2*math.pi*ph)*(1 if side else .40)
        if coupled:
            # Same physical near/far leg drives its opposing arm, not a separate clock.
            stride=cfg['stride']*scale*(1 if side else .20)
            gait_center=sum(parts[k+'_shin']['end'][0] for k in ('left','right'))/2 if simple else shin['end'][0]
            raw_signal=(path['target'][0]-gait_center)*direction/(stride/2)
            signal=raw_signal/math.sqrt(1+raw_signal*raw_signal)
            swing=cfg['arm']*rig.get('armSwingScale',1)*signal
        theta=math.pi/2+swing*direction+lean
        elbow=add(shoulder,rotate([length(sub(upper['end'],upper['start'])),0],theta));flex=.9 if action=='dash' else .22
        if rig.get('gaitProfile') in ('evidence-v1','coupled-v2'):flex=(.9+.18*math.sin(2*math.pi*ph)) if action=='dash' else (.12+.06*(1-math.cos(2*math.pi*ph))/2)
        if coupled:flex=(1.05-.18*signal) if action=='dash' else (.18-.08*signal)
        if action=='walk' and rig.get('armMotion')=='shoulder-led':
            # Pose shoulder/elbow directly. A wrist target must not overbend the elbow.
            arm_a=length(sub(upper['end'],upper['start']));arm_b=length(sub(fore['end'],fore['start']))
            driver=signal if coupled else math.cos(2*math.pi*ph)
            theta=math.pi/2+direction*.55*driver*rig.get('armSwingScale',1)+lean
            foretheta=theta-direction*.35
            elbow=add(shoulder,rotate([arm_a,0],theta));wrist=add(elbow,rotate([arm_b,0],foretheta))
            diagnostics[-1].update(armReachErrorPx=0,wrist=wrist,shoulder=shoulder,couplingSignal=driver,armMotion='shoulder-led')
        elif coupled:
            # Match wrist excursion to actual step reach. Preserve both arm bones via IK.
            arm_a=length(sub(upper['end'],upper['start']));arm_b=length(sub(fore['end'],fore['start']))
            down=(arm_a+arm_b)*(.72 if action=='dash' else (.82 if simple else (.90 if wide_stable else .94)))
            # A small pumping arc follows this same leg's motion/velocity, not a second clock.
            index=0 if s=='left' else 1;h=1e-4
            before=foot_path(rig,s,index,phase-h,cfg,action)['target'][0];after=foot_path(rig,s,index,phase+h,cfg,action)['target'][0]
            velocity=direction*(after-before)/(2*h*(stride/2))
            down+=3*signal if simple else (3 if action=='dash' else 1.5)*signal+(2 if action=='dash' else .8)*math.tanh(velocity/6)
            wrist=[shoulder[0]+direction*((6 if action=='dash' else 0)-signal*stride*(.82 if action=='dash' else (.78 if simple else .62))*rig.get('armSwingScale',1)),shoulder[1]+down]
            elbow,wrist,arm_clamp=ik(shoulder,wrist,arm_a,arm_b,direction)
            theta=angle(sub(elbow,shoulder));foretheta=angle(sub(wrist,elbow));diagnostics[-1]['armReachErrorPx']=arm_clamp;diagnostics[-1]['wrist']=wrist;diagnostics[-1]['shoulder']=shoulder;diagnostics[-1]['couplingSignal']=signal
        else:foretheta=theta-direction*flex
        out[s+'_upper_arm']=(shoulder,theta);out[s+'_forearm']=(elbow,foretheta)
    if action=='walk' and rig.get('walkProportions'):
        from proportions import retarget_pose
        out=retarget_pose(rig,out,diagnostics)
    return out,diagnostics

def validate(rig, image=None):
    if 'walkHipDrive' in rig:
        c=rig['walkHipDrive'];fields={'confirmed','pelvisShift','pelvisTilt','torsoCounter','swingLead'}
        if not isinstance(c,dict) or not fields<=set(c) or bool(set(c)-fields-{'gaitCenter'}) or c.get('confirmed') is not True:raise ValueError('Confirm complete walkHipDrive calibration')
        if 'gaitCenter' in c and c['gaitCenter']!='source-ankles':raise ValueError('Unknown walkHipDrive gaitCenter')
        if rig.get('view')!='side' or rig.get('walkStyle')!='simple' or rig.get('walkHipRegistration')!='source':raise ValueError('walkHipDrive needs side simple source hip registration')
        for key,maximum in [('pelvisShift',8),('pelvisTilt',.12),('torsoCounter',.05),('swingLead',.35)]:
            value=c[key]
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=maximum:raise ValueError('walkHipDrive calibration outside range: '+key)
    if rig.get('walkHipRegistration','legacy-centered') not in ('legacy-centered','source'):raise ValueError('Unknown walkHipRegistration')
    if rig.get('walkHipRegistration')=='source' and (rig.get('view')!='side' or rig.get('walkStyle')!='simple'):raise ValueError('Source hip registration needs side simple walk')
    if rig.get('armPose','legacy') not in ('legacy','held-source'):raise ValueError('Unknown armPose')
    if rig.get('armPose')=='held-source' and rig.get('view')!='side':raise ValueError('held-source arm pose needs side view')
    from projected_walk import validate as validate_projected
    validate_projected(rig)
    from proportions import validate_proportions
    validate_proportions(rig)
    if rig.get('legRecovery','legacy') not in ('legacy','clear-step'):raise ValueError('Unknown legRecovery')
    if rig.get('legRecovery')=='clear-step' and (rig.get('view')!='side' or rig.get('walkStyle')!='simple' or rig.get('legSwing')!='thigh-led'):raise ValueError('clear-step needs side simple thigh-led walk')
    if rig.get('walkPosture','legacy') not in ('legacy','upright'):raise ValueError('Unknown walkPosture')
    if rig.get('walkPosture')=='upright' and (rig.get('view')!='side' or rig.get('walkStyle')!='simple'):raise ValueError('upright posture needs side simple walk')
    from hip_cloth import validate_attachment
    validate_attachment(rig)
    from ownership import validate_ownership
    validate_ownership(rig)
    from skin_shape import validate_skin_shape
    validate_skin_shape(rig)
    from garment import validate_garment
    validate_garment(rig)
    if rig.get('legSwing','legacy') not in ('legacy','thigh-led'):raise ValueError('Unknown legSwing')
    if rig.get('legSwing')=='thigh-led' and (rig.get('view')!='side' or rig.get('walkStyle')!='simple'):raise ValueError('thigh-led recovery needs side-view simple walk')
    if rig.get('armMotion','legacy') not in ('legacy','shoulder-led'):raise ValueError('Unknown armMotion')
    if rig.get('armMotion')=='shoulder-led' and rig.get('view')!='side':raise ValueError('shoulder-led arms are side-view only')
    if rig.get('walkStyle')=='simple' and rig.get('view')!='side':raise ValueError('simple walk is side-view only')
    if rig.get('walkStyle','cautious') not in ('cautious','purposeful','wide-stable','simple'):raise ValueError('walkStyle must be cautious/purposeful/wide-stable/simple')
    if rig.get('gaitProfile','legacy') not in ('legacy','evidence-v1','coupled-v2'): raise ValueError('Unknown gaitProfile')
    if rig.get('view') not in ('front','side','back'): raise ValueError('view must be front/side/back')
    for field,low,high in [('motionScale',.1,2.0),('pelvisDrop',0.0,20.0),('armSwingScale',0.0,1.5)]:
        value=rig.get(field,1.0 if field in ('motionScale','armSwingScale') else 0.0)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:raise ValueError(field+' outside supported calibration range')
    if not isinstance(rig.get('preserveReach',False),bool): raise ValueError('preserveReach must be boolean')
    if rig.get('facing','right') not in ('left','right'): raise ValueError('facing must be left/right')
    if set(rig.get('parts',{})) != set(PARTS): raise ValueError('All 12 rigid parts are required')
    def point(v):
        if not isinstance(v,list) or len(v)!=2 or not all(isinstance(n,(float,int)) and math.isfinite(n) and 0<=n<=384 for n in v): raise ValueError('Coordinates must be finite [0,384] pairs')
    point(rig['root'])
    order=rig.get('order',PARTS)
    if len(order)!=len(PARTS) or set(order)!=set(PARTS): raise ValueError('order must contain every part exactly once')
    if 'waistAttachment' in rig:
        w=rig['waistAttachment']
        if not isinstance(w,dict) or not {'startFraction','endFraction'}<=set(w)<={'startFraction','endFraction','ankleContinuity'}:raise ValueError('waistAttachment needs startFraction/endFraction and optional ankleContinuity')
        if not isinstance(w.get('ankleContinuity',False),bool):raise ValueError('ankleContinuity must be boolean')
        if not all(isinstance(w[k],(int,float)) and not isinstance(w[k],bool) and math.isfinite(w[k]) for k in ('startFraction','endFraction')):raise ValueError('Invalid waist fractions')
        if not 0<=w['startFraction']<w['endFraction']<=1:raise ValueError('Waist fractions must satisfy0<=start<end<=1')
    mesh_used=set();meshes=rig.get('jointMeshes',[])
    if not isinstance(meshes,list) or len(meshes)>4:raise ValueError('jointMeshes must be a list of at most4 pairs')
    for m in meshes:
        if not isinstance(m,dict):raise ValueError('joint mesh entry must be an object')
        parent=m.get('parent');child=m.get('child');radius=m.get('radius',10)
        allowed=[(s+'_'+a,s+'_'+b) for s in ('left','right') for a,b in [('upper_arm','forearm'),('thigh','shin')]]
        if (parent,child) not in allowed or parent in mesh_used or child in mesh_used:raise ValueError('Invalid/overlapping joint mesh pair')
        if isinstance(radius,bool) or not isinstance(radius,(int,float)) or not math.isfinite(radius) or not 2<=radius<=36:raise ValueError('Joint mesh radius must be 2..36px')
        if m.get('walkContour','rotation') not in ('rotation','centerline'):raise ValueError('Unknown walkContour')
        if m.get('walkContour')=='centerline' and not parent.endswith('_thigh'):raise ValueError('centerline contour is for thigh/shin pairs only')
        cuff=m.get('walkCuffNormal')
        if 'walkCuffNormal' in m:
            if not isinstance(cuff,dict) or set(cuff)!={'startY','endY'}:raise ValueError('walkCuffNormal needs startY/endY')
            if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in cuff.values()) or not 0<cuff['startY']<cuff['endY']<=384:raise ValueError('Invalid walkCuffNormal source band')
            if rig.get('view')!='side' or rig.get('walkStyle')!='simple' or m.get('walkContour')!='centerline' or not parent.endswith('_thigh'):raise ValueError('walkCuffNormal requires side simple centerline thigh mesh')
        depth=m.get('walkAnkleDepth',0)
        if isinstance(depth,bool) or not isinstance(depth,(int,float)) or not math.isfinite(depth) or (depth!=0 and not 4<=depth<=24):raise ValueError('walkAnkleDepth must be 0 or 4..24px')
        if depth and (not parent.endswith('_thigh') or rig.get('view')!='side'):raise ValueError('walkAnkleDepth requires side thigh/shin mesh')
        offset=m.get('walkAnkleOffsetX',0)
        if isinstance(offset,bool) or not isinstance(offset,(int,float)) or not math.isfinite(offset) or not -4<=offset<=4:raise ValueError('walkAnkleOffsetX must be -4..4 source pixels')
        if offset and (not depth or not parent.endswith('_thigh') or rig.get('view')!='side'):raise ValueError('Ankle art offset requires side thigh ankle attachment')
        shape=m.get('walkClothWidth')
        if shape is not None:
            if not isinstance(shape,dict) or set(shape)!={'scale','fullUntil','fadeEnd'}:raise ValueError('walkClothWidth needs scale/fullUntil/fadeEnd')
            if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in shape.values()):raise ValueError('Invalid cloth width calibration')
            if not .65<=shape['scale']<=1 or not 0<=shape['fullUntil']<shape['fadeEnd']<=384 or shape['fadeEnd']-shape['fullUntil']<2:raise ValueError('Cloth width range invalid')
            if not parent.endswith('_thigh') or rig.get('view')!='side' or rig.get('walkStyle')!='simple' or not rig.get('hipAttachment'):raise ValueError('Cloth width requires side simple split-cloth thigh mesh')
            if not rig['parts'][parent]['start'][1]<=shape['fullUntil']<shape['fadeEnd']<=rig['parts'][child]['start'][1]:raise ValueError('Cloth width transition must end above knee')
        mesh_used.update([parent,child])
    if 'waistAttachment' in rig and not all(s+'_thigh' in mesh_used for s in ('left','right')):raise ValueError('waistAttachment requires both thigh/shin meshes')
    for name,p in rig['parts'].items():
        if p.get('availability','available') not in ('available','unverified','missing'): raise ValueError('Invalid part availability')
        point(p['start']);point(p['end'])
        if 'soleOutline' in p:
            if not 3<=len(p['soleOutline'])<=100:raise ValueError('soleOutline needs 3..100 convex-hull points')
            for v in p['soleOutline']:point(v)
        for marker in ('forefootContact','heelContact'):
            if marker in p:point(p[marker])
        if length(sub(p['end'],p['start']))<2: raise ValueError(name+': pivots must be at least 2px apart')
        if len(p['polygon'])<3 or len(p['polygon'])>100: raise ValueError(name+': polygon needs 3..100 vertices')
        for v in p['polygon']: point(v)
    for s in ('left','right'):
        for parent,child in [('thigh','shin'),('shin','foot'),('upper_arm','forearm')]:
            if length(sub(rig['parts'][s+'_'+parent]['end'],rig['parts'][s+'_'+child]['start']))>1:
                raise ValueError(f'{s}: {parent} end and {child} start must coincide (within 1px)')
    if image and image.size!=SIZE: raise ValueError('Normalized canvas must be 384x384')

def require_ready(rig):
    validate(rig)
    unavailable=[name for name,p in rig['parts'].items() if p.get('availability','available')!='available']
    if unavailable:raise ValueError('Missing/unverified artwork: '+', '.join(unavailable))
    if rig.get('confirmed') is not True or not all(p.get('confirmed') is True for p in rig['parts'].values()):raise ValueError('Confirm every mask/pivot and visible or supplied artwork first')

def cutouts(image,rig):
    result={}
    for name,p in rig['parts'].items():
        mask=Image.new('L',SIZE); ImageDraw.Draw(mask).polygon([tuple(x) for x in p['polygon']],fill=255)
        from PIL import ImageChops
        layer=image.copy(); layer.putalpha(ImageChops.multiply(image.getchannel('A'),mask));result[name]=layer
    return result

def compose_pose(rig,layers,transforms,mesh_diagnostics=None,action=None):
    """Apply rigid transforms; shared by neutral registration review and animation."""
    from proportions import active_rig,display_image
    rig=active_rig(rig,action)
    if action=='walk' and rig.get('hipAttachment'):
        from hip_cloth import prepare
        rig,layers,transforms=prepare(rig,layers,transforms)
    frame=Image.new('RGBA',SIZE)
    meshes=rig.get('jointMeshes',[]);mesh_parents={m['parent']:m for m in meshes};mesh_children={m['child'] for m in meshes}
    for name in rig.get('order',PARTS):
        if name in mesh_children:continue
        if name in mesh_parents:
            from joint_mesh import draw_joint
            m=mesh_parents[name];stats={} if mesh_diagnostics is not None else None;frame.alpha_composite(draw_joint(rig,layers,transforms,name,m['child'],m.get('radius',10),diagnostics=stats,contour=m.get('walkContour','rotation') if action=='walk' else 'rotation',ankle_depth=m.get('walkAnkleDepth',0) if action=='walk' else 0,cloth_width=m.get('walkClothWidth') if action=='walk' else None,ankle_offset=m.get('walkAnkleOffsetX',0) if action=='walk' else 0,cuff_normal=m.get('walkCuffNormal') if action=='walk' else None))
            if mesh_diagnostics is not None:mesh_diagnostics.append(dict(parent=name,child=m['child'],**stats))
            continue
        part=rig['parts'][name];dest,theta=transforms[name];delta=theta-angle(sub(part['end'],part['start']))
        c=math.cos(delta);s=math.sin(delta);x,y=part['start'];dx,dy=dest
        moved=layers[name].transform(SIZE,Image.Transform.AFFINE,(c,s,x-c*dx-s*dy,-s,c,y+s*dx-c*dy),Image.Resampling.BICUBIC)
        frame.alpha_composite(moved)
    return display_image(rig,frame)

def render_neutral(rig,layers):
    validate(rig)
    if rig.get("projectedWalk"):
        from projected_walk import render as projected_render
        return projected_render(rig,layers,0,True)[0]
    transforms={name:(p['start'],angle(sub(p['end'],p['start']))) for name,p in rig['parts'].items()}
    if rig.get('walkProportions'):
        from proportions import retarget_pose
        return compose_pose(rig,layers,retarget_pose(rig,transforms),action='walk')
    return compose_pose(rig,layers,transforms)

def render(rig,layers,action,t):
    if rig.get('projectedWalk'):
        if action!='walk':raise ValueError('Front/back projected dash is not calibrated')
        from projected_walk import render as projected_render
        im,stats=projected_render(rig,layers,t)
        return im,[{'side':side,'contact':(t+j*.5)%1<.6,'projectionDiagnostics':stats} for j,side in enumerate(('left','right'))]
    transforms,diag=pose(rig,action,t)
    meshes=[];frame=compose_pose(rig,layers,transforms,meshes,action=action)
    if meshes:diag[0]['jointMeshDiagnostics']=meshes
    return frame,diag

def export(rig,layers,action,frames=None):
    if rig.get('projectedWalk'):
        from projected_walk import export as projected_export
        return projected_export(rig,layers,action,frames)
    if frames is None:frames=8 if action=='walk' and rig.get('walkStyle')=='simple' else 24
    require_ready(rig); cfg=gait_config(rig,action);sheet=Image.new('RGBA',(384*6,384*math.ceil(frames/6))); records=[]; all_diag=[]
    for i in range(frames):
        image,diag=render(rig,layers,action,i/frames); x=(i%6)*384;y=(i//6)*384;sheet.paste(image,(x,y));all_diag+=diag
        records.append(dict(index=i,rect=dict(x=x,y=y,w=384,h=384),time=i/frames*cfg['duration'],contacts=[d['side'] for d in diag if d['contact']]))
    reach=max(d['reach_error'] for d in all_diag)
    mesh_stats=[m for d in all_diag for m in d.get('jointMeshDiagnostics',[])]
    # Imported shapes may clip even when skeleton fits; explicitly flag this.
    border=False; out_of_bounds=set();bridge_stats=[];seam_stats=[]
    for i in range(frames):
        transforms,_=pose(rig,action,i/frames)
        from proportions import active_rig,display_point
        boundsrig,boundslayers=active_rig(rig,action),layers
        if action=='walk' and rig.get('hipAttachment'):
            from hip_cloth import prepare
            boundsrig,boundslayers,transforms=prepare(boundsrig,layers,transforms,bridge_stats)
        for name,layer in boundslayers.items():
            if name not in boundsrig['parts']:continue
            box=layer.getbbox()
            if not box: continue
            x0,y0,x1,y1=box; dest,theta=transforms[name]; part=boundsrig['parts'][name]
            delta=theta-angle(sub(part['end'],part['start']))
            points=[add(dest,rotate(sub(p,part['start']),delta)) for p in ([x0,y0],[x1,y0],[x1,y1],[x0,y1])]
            points=[display_point(boundsrig,p) for p in points]
            if any(x<0 or y<0 or x>384 or y>384 for x,y in points): out_of_bounds.add(name)
        im,_=render(rig,layers,action,i/frames)
        if action=='walk' and rig.get('walkGarment'):
            from seam_quality import measure_seams
            seam_stats.extend(measure_seams(boundsrig,boundslayers,transforms,im))
        a=im.getchannel('A'); border |= any(a.crop(box).getbbox() for box in [(0,0,384,1),(0,383,384,384),(0,0,1,384),(383,0,384,384)])
    # Verify virtual-world contact drift over densely sampled stance intervals.
    slip=0.0; previous={}
    for i in range(241):
        t=i/240; _,ds=pose(rig,action,t)
        for d in ds:
            key=d['side']; world=[d['contactPoint'][0]+d['ground_velocity']*t*cfg['duration'],d['contactPoint'][1]]
            if d['contact'] and key in previous and previous[key][0] and previous[key][2]==d['contactMode']:
                # phase wrap denotes a new contact, not one continuous plant.
                oldphase=(t-1/240+(0 if key=='left' else .5))%1
                newphase=(t+(0 if key=='left' else .5))%1
                if newphase>=oldphase: slip=max(slip,length(sub(world,previous[key][1])))
            previous[key]=(d['contact'],world,d['contactMode'])
    metadata=dict(schema='sprite-motion-lab/v0.1',status='draft',view=rig['view'],facing=rig.get('facing','right'),action=action,canvas={'w':384,'h':384},
      alpha=True,hipRootOverlap=(bool(rig.get('hipAttachment',{}).get('rootOverlap',False)) if action=='walk' else False),walkOwnershipParts=(sorted(rig.get('walkOwnership',{}).get('keepPolygons',{})) if action=='walk' else []),legRecovery=(rig.get('legRecovery','legacy') if action=='walk' else 'legacy'),walkMaterialParts=(sorted(n[5:] for n in layers if n.startswith('walk:')) if action=='walk' and rig.get('hipAttachment') else []),walkPosture=rig.get('walkPosture','legacy'),hipCloth=(rig.get('hipAttachment',{}).get('mode','legacy') if action=='walk' else 'legacy'),legSwing=rig.get('legSwing','legacy'),armMotion=rig.get('armMotion','legacy'),walkStyle=rig.get('walkStyle','cautious'),effectiveGaitProfile=('coupled-v2' if action=='walk' and rig.get('walkStyle') in ('purposeful','wide-stable','simple') else rig.get('gaitProfile','legacy')),gaitProfile=rig.get('gaitProfile','legacy'),stanceFraction=cfg['stance'],rootPivot=(display_point(active_rig(rig,action),[rig['root'][0],rig['root'][1]-rig['walkProportions']['bodyRise']]).tolist() if action=='walk' and rig.get('walkProportions') else rig['root']),sourceRootPivot=rig['root'],duration=cfg['duration'],fps=frames/cfg['duration'],frames=records,
      walkCuffNormals=([{'parent':m['parent'],**m['walkCuffNormal']} for m in rig.get('jointMeshes',[]) if m.get('walkCuffNormal')] if action=='walk' else []),walkProportions=(rig.get('walkProportions') if action=='walk' else None),walkGarment=(rig.get('walkGarment') if action=='walk' else None),walkSkinShape=(rig.get("walkSkinShape") if action=="walk" else None),walkClothWidths=([{'parent':m['parent'],**m['walkClothWidth']} for m in rig.get('jointMeshes',[]) if m.get('walkClothWidth')] if action=='walk' else []),walkAnkleAttachments=([{'parent':m['parent'],'depth':m['walkAnkleDepth'],'offsetX':m.get('walkAnkleOffsetX',0)} for m in rig.get('jointMeshes',[]) if m.get('walkAnkleDepth')] if action=='walk' else []),motionSpace='in-place; contact foot moves opposite virtual root velocity',quality={'garmentInternalSeamMinAlpha':min((v['alpha'] for v in seam_stats),default=None),'garmentInternalSeamSamples':len(seam_stats),'garmentInternalSeamWarning':bool(action=='walk' and rig.get('walkGarment') and (not seam_stats or any(v['alpha']<220 for v in seam_stats))),'hipBridgeMinimumAreaRatio':min((v['areaRatio'] for v in bridge_stats),default=1),'missingContactMarkers':([s for s in ('left','right') if not all(k in rig['parts'][s+'_foot'] for k in ('forefootContact','heelContact'))] if rig.get('gaitProfile') in ('evidence-v1','coupled-v2') or (action=='walk' and rig.get('walkStyle') in ('purposeful','wide-stable','simple')) else []),'maxReachErrorPx':reach,'maxRecoveryFootAdjustmentPx':max(d.get('recoveryFootAdjustmentPx',0) for d in all_diag),'maxArmReachErrorPx':max(d.get('armReachErrorPx',0) for d in all_diag),'meshMaxActiveInvertedTriangles':max((m['activeInvertedTriangles'] for m in mesh_stats),default=0),'meshMinimumActiveAreaRatio':min((m['minimumActiveAreaRatio'] for m in mesh_stats),default=1),'meshCompressionWarning':(any(m['minimumActiveAreaRatio']<.2 for m in mesh_stats) or any(m['areaRatio']<.2 for m in bridge_stats)),'maxSupportCorrectionPx':max(d['supportCorrectionPx'] for d in all_diag),'maxContactStepSlipPx':slip,'contactMetric':'world marker displacement within same mode; sole-envelope rolling can move marker vertically; not raster clearance proof','contactSampleHz':240/cfg['duration'],'conservativeBoundsWarnings':sorted(out_of_bounds),'borderAlpha':bool(border),'approved':False},
      limitations=['Rigid cutouts with optional localized joint-mesh deformation; no automatic hidden artwork inference','No automatic quality approval','Front/back gait is a planar stylization, not 3D reconstruction'])
    return sheet,metadata
