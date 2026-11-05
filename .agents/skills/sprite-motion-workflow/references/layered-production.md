# Layered production corrections

Use the companion `layered_motion.py` for explicitly authored full-canvas layers/poses when fixed source head/torso plus independent limbs is appropriate. Read its `docs/LAYERED_MOTION.md` for schema and strip-warp limits. It is not automatic extraction, rigging, grounding or natural-motion certification.

Before animation, compare full neutral source-alpha coverage and isolate semantic owners. Retain ink/AA outlines with their real hands/legs, not the fixed skirt/body. A generated complete hand plus a cropped original hand creates duplicate contours; select one visible silhouette owner. Overlap can be intentional for hidden socket surfaces; zero overlap is not a quality goal.

Neutral coverage does not prove moving attachment. Inspect both shoulder roots across emergence, source-connected socket surfaces, full sleeve volume/cuff and shoulder–elbow–wrist chain. Thumb location alone does not establish palm surface. Removing a carried object can require torso/shoulder pose reconstruction, not merely filling the hole. Keep inferred surfaces explicit.

The optional support-height helpers use stance legs only. A periodic Fourier fitter can smooth authored stance constraints, but inspect its residual/reach diagnostics and dense unsampled poses; smoothness is not exact contact. Do not let airborne reach lower the body. Test every exported frame and dense intermediate phases around both support exchanges, plus last→first. Four clean keys can conceal body drops, knee snaps and unintended direction changes. Reconsider old reach-clamped ankles after a height repair; continuous but persistently crouched motion is not automatically acceptable.

Use one physical phase/depth convention for legs and arms. Front/back visible elbow bend, forearm overlap, foreshortening and occlusion must actually read correctly in plain drawings. Numeric correlation or a field named opposition is not proof. Distinguish observed source landmarks from hidden-joint inference and compare both contact extremes before accepting registration.

Use `production_audit.py` to diagnose omitted/overlapping neutral alpha, timestamp-based landmark movement, repeated frames and artifact-bound temporal records. It cannot assign semantic pixel owners or watch animation. Preserve source scale/identity. Sample a loop on [0,1), inspect the real last→first join, and do not count extended holds as new drawings. Apply the normal-speed gate in [quality.md](quality.md); unobserved playback remains UNREVIEWED.
