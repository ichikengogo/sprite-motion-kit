# Production checks that geometry alone misses

## Sources and ownership

Keep each original byte-for-byte and record its source/license separately. Compare the actual three views for identity, proportions, clothing, accessories, hand conditions and orientation. A missing view remains missing until explicitly authored; a mirrored side is not a new view.

Before rigging, isolate each full RGBA layer and compare the union of its alpha to the canonical neutral. Include faint antialias/ink pixels. Uniform row cutoffs can clip hair, hoods, sloping waist bands or hems. Color segmentation can leave dark hand/calf outlines embedded in the fixed torso. Explain omitted pixels explicitly, and inspect semantic ownership even when numeric coverage is perfect.

Give each complete hand/shoe/sock exactly one visible silhouette owner. Combining a generated full limb with an original partial limb can create duplicate fingers or shoes. Retain a generated sleeve only to the cuff if the original hand is the chosen owner. Hidden authored overlap is permitted and often necessary; a zero-overlap union is not a universal quality goal.

`production_audit.ownership_report(source, layers)` returns counts and a colored overlay: magenta omitted source, cyan added, amber overlapping. It does not decide whether those regions are correct.

## Shoulder, hand and clothing surfaces

Review both near and far roots in isolation and throughout emergence. A rounded cap may look dislocated despite connected alpha. Keep the shoulder–elbow–wrist chain coherent and full sleeve circumference; independently narrowing or shifting a sleeve can pinch the elbow. A source-connected socket needs intentional hidden overlap throughout movement, not only a neutral match.

Hand surface follows the source and physical owner: palm, dorsal, edge, mixed or uncertain. An anterior thumb does not prove a palm; inspect thenar pad, crease and curled finger pads versus nails/dorsal knuckles. Do not apply a left-facing relaxed-arm rule to other views, held objects or rotated wrists.

Removing a carried object may require reconstruction of pose and anatomy, not simple erasure. Keep torso attitude, shoulder root, strap/wrist attachment and the scope of newly authored pixels explicit. Inspect the entire garment outline, waist/seat, crotch, cuffs and hem, not a narrow seam ROI. Do not add a second complete pair of shorts or use a flat rectangle to hide a gap.

## Physical motion and projection

Support/recovery must visibly alternate with thigh-led motion. Track stable physical owners rather than screen-left/right. Opposed endpoint signs are insufficient if independently projected elbows/feet suggest the wrong depth. Front and back must use the appropriate inverse camera relation and show plausible elbow bend/overlap, not merely a vertically lifted hand.

Separate observed landmarks from inferred hidden joints. Bad hidden-hip registration can make equal-amplitude tracks read as wide-contact/narrow-contact limping. Calibrate from the actual new source; never reuse another character's coordinates or costume assumptions.

Evaluate every exported phase plus dense intermediate phases for a continuous rig. Four good keys can hide abrupt body drops or knee snaps during support exchange. Use grounded supports to constrain height; airborne reach should not dictate the body height. After a height repair, recheck whether old ankle clamps preserve the original snap. Continuity alone is not naturalness if it produces prolonged crouching or shuffling.

`production_audit.py tracks` reads `{"tracks": {"sole": [[x,y], ...]}, "durationsMs": [...]}` and reports actual step speed/acceleration including last→first. These are measured/authored points, not automatic image tracking. There is no universal threshold; interpret support state and in-place travel correctly.

## Time, loop, identity and review

Use a fixed canvas and one constant scale per view. Preserve head/hair/face/torso identity across time, not just in isolated poses. Do not fix jitter by reducing an otherwise required walk to shuffling. Sample periodic rigs on `[0,1)` and check the actual exported order, durations, repeated end frame and last→first join. Intentional holds are allowed but are not missing intermediate drawings.

`production_audit.py frames FRAME_DIR --durations durations.json --out report.json` reports adjacent identical RGBA frames and duplicate endpoint. It does not automatically reject deliberate holds. Normal-color images should be reviewed before numeric “pass” summaries.

Observe the exact final loop at 1x, native and target small size, including multiple full cycles when practical. Record actual reviewer, observation tool, artifact hash, speed, actual loop counts, concrete support/identity/cloth/arm findings and unresolved defects. If continuous observation is unavailable, use `unreviewed` or `blocked` with null unobserved counts. Never manufacture those fields from static inspection.

`production_audit.py temporal RECORD ARTIFACT --out report.json` validates the record's structure/hash only. `drawn_cel.py` also validates the matching animated artifact, 1x observation metadata, tool, concrete findings and actual complete-loop counts for native/128 views. Neither proves the claimed observation occurred. User acceptance and independent art review remain separate from technical checks.

For a local repair, freeze the previous output, author the legitimate allowed region, compare outside-region RGBA exactly, retain timing and rerender from a reopened portable project. Broad all-white masks prove no localization. Deliver unresolved limits plainly; do not call known identity drift or detached anatomy acceptable merely because a different defect improved.
