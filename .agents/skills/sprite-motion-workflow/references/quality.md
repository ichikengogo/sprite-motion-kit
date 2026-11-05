# Visual evidence, not test-count completion

Before segmentation, compare all three originals for identity: visible face, hair, clothes, accessories, shoes and unexplained proportion differences. Record orientation and resolve mismatches; a matching hash cannot establish character identity.

Use original / previous accepted / candidate at equal head pixel scale and ground alignment; show neutral plus each displayed pose. If the user explicitly changes proportions, label intentional differences instead of defending fixed bone lengths. Manual landmarks are not anatomy truth.

- **Ownership:** isolate and color-code every thigh/shin/shoe/cloth layer. Trace suspicious pixels to source coordinates. A near shin can contain an embedded far shin or sock even when the composite appears to show two valid legs. Never erase a genuine overlap boundary as a shortcut.
- **Ink:** inspect true dark contours and AA on skin AND sock separately. Alpha masks must keep the real line, not shave into pale interior. Source changes invalidate confirmation. Restoring an upper sock edge must not restore the obsolete shoe collar below it.
- **Heel:** for continuous rig animation, isolate rendered distal shin and rigid shoe for every key and at least 24 phases. For drawn cels inspect every actual cel; repeated holds are not new intermediate poses. Compare heel pixels to shoe opening in shoe-local coordinates, identify ROI/tolerance explicitly. Zero ankle-marker slip does not prove raster containment. Retain legitimate heel tabs, avoid enlarging shoes to cover errors.
- **Cloth:** one shared waist/seat plus plausible moving leg openings, no apron triangle or extra fixed tabs. Inspect the ENTIRE garment boundary: upper shirt/waist seam, front/side transitions, crotch and both cuffs. Endpoint coincidence does not ensure a mapped curved hem joins skin. Test alpha of interior seam support and use cyan, magenta, black and checkerboard backgrounds. Gray can conceal real holes. Narrow sampled ROI success is not full coverage proof.
- **Geometry:** check active triangles and dense loop phases for folds, but a positive Jacobian does not guarantee preserved volume. Inspect knee corners and straight shin segments, sock taper, elbow bulges and attachment gaps. Reject rubber limbs, inverted patches, or reduced stride used merely to hide defects.
- **Motion:** contact/down/passing/up should visibly differ, two feet remain readable, arm/leg opposition should be visible rather than merely sinusoidal. Foot recovery must clear ground with heel/toe pixels, not ankle alone. Keep head/torso pitch stable when requested; root proxy is not mass-weighted COM. Preserve real walking support/no fake flight. Review dash independently.
- **Proportions:** fixed canvas, original head/chin/shoulder/hip/knee/ankle/sole and hem landmarks, visible hem-to-sole span. Separate bone length, pose foreshortening, cloth coverage, and local surface deformation. Fixed global neutral-height fit must retain bobbing and shoe aspect ratio.
- **Delivery:** all actual exported keys at native and 128 canvas, same loop timing, matched defect crops and whole-body proof. Continuous rigs additionally require 24 intermediate phases on contrasting backgrounds. Drawn-cel loops require every real cel and actual timing/last→first review; do not claim synthesized intermediates from repeated holds. Read saved project back and compare actual export RGBA/metadata/frame count/period/pivot; preserve previous action outputs when outside scope. A reviewer should inspect normal-color images before seeing numeric pass claims.

Stop and report missing material/ambiguous ownership or unresolved visible defects. AI-inferred hidden regions require review and provenance; neither three inputs nor passing unit tests guarantee a finished character.

## Drawn-cel-specific rejection checks

Read [drawn-cel workflow](drawn-cel.md). Trace near/far identities through both half-cycles: repeating the same four poses with slightly changed color is not walking. Compare source and assembled rear waist before/after ownership clipping; a horizontal shelf can look detached while alpha remains connected. Check full outer cuff circumference and skin exposure, not knee centerline alone. One shared upper source stabilizes face/bag only if its content and intended transform remain unchanged.

Automated structural checks can detect exact repeated half-cycles, invalid declared owners, stale sources/evidence, missing assets and output mismatch. They cannot establish correct depicted owners, semantic garment length, natural contact or attractive motion; those require explicit reviewed images and notes. Reviewers should not see a numeric pass banner as a substitute for the actual loop.

## Adjacent-cel and temporal art gate

Single-pose phase labels are insufficient: compare each drawing with its two actual neighbors and original identity reference. “Up” must show the intended forefoot push/recovery rather than merely a second down pose. Trace a recovery leg forward into the next pose. Repair only the failed interval using both endpoint images, not an isolated text label. Keep free arms free with appropriate opposition, or held hands attached according to the per-view source condition.

Mark a consistent sole/heel point through actual timestamps; compare consecutive marker distance divided by elapsed time against support/recovery state. Large unmotivated changes flag pose jumps. There is no universal speed cutoff, and in-place stance travel is not automatically foot sliding. Longer holds change timing, not the missing drawing.

Review face, hair silhouette and torso proportions as a time sequence at constant reference scale, not just a static sheet or alpha test. Real bob/foreshortening differs from eye/cheek/hairstyle/body-size drift. Record remaining flicker or staccato honestly. Neither numerical markers nor review records guarantee natural or appealing motion.

## Mandatory real-time temporal review — an art acceptance gate

A normal-speed motion review is required before independently certifying temporal quality. A clearly labeled candidate may still be delivered for user review; user acceptance and independent temporal certification are separate records. A contact sheet, extracted GIF frames, GIF duration metadata, matching RGBA bytes or passing tests **is not real-time playback inspection**. Do not say “watched the GIF” when only stills or timestamps were available. “Improved prototype” or “presentation possible” is not a substitute for acceptance of the actual motion.

Record all of the following in temporal review evidence:
- Reviewer identity (human or named agent) and the actual observation method/tool.
- Exact reviewed GIF/video artifact path and SHA-256; distinguish alternatives and retimed versions.
- Playback speed (normal 1× required), native-size and 128px viewing, and the actual number of complete loops observed at each size.
- Observations across consecutive frames and the last→first join: physical support/recovery continuity, contact/foot travel, pelvis/torso connection, face/head/hair/torso scale stability, clothing/accessory continuity, and source-specific free-arm or held-contact behavior.
- Explicit outcome: accepted for the stated scope, rejected with defects, or **BLOCKED / UNREVIEWED**. A bare checkbox or copied “looks natural” note is insufficient.

If no available tool or reviewer can actually observe normal-speed video/animation, mark this gate **BLOCKED / UNREVIEWED**, state that only still-frame/structural checks were completed, and request appropriate real-time review. Do not infer smoothness from extracted frames or fabricate a playback method, loop count or observation. Continue safe authorized local repairs and static/alpha/reproduction checks. Clearly labeled candidates may be shared for user review within the task, with temporal status unreviewed; this does not certify smoothness or require approval for every intermediate.

Known identity, head/torso scale or silhouette jitter is a **rejection**, not a tolerated shipping limitation merely because another defect improved. Likewise reject unresolved support-foot jumps, reversing recovery, or visibly discontinuous body/cloth motion. Keep the previous accepted baseline; preserve the failed candidate as evidence, not as a new quality baseline.

When independent full-cel drawings cannot retain identity/scale, consider a different representation before more generation: an immutable source head/torso, independently authored free-arm layers (when the source calls for arm swing), and coherent whole-pelvis/leg authored layers. Held contacts need their own source-faithful attachment handling. This is a design alternative requiring ownership, occlusion, seam and real-time review—not an implemented automatic fix or a guarantee of natural motion. Do not freeze free arms merely to stabilize the face, and do not split pelvis/garment back into the rejected deforming pieces.

### Temporal evidence record (fill only from actual observation)

Keep a project-local report alongside any real playback recording or observation notes. Required fields: `reviewer`, `methodTool`, `artifactPath`, `artifactSha256`, `speed`, `nativeCompleteLoopsObserved`, `size128CompleteLoopsObserved`, `continuityFindings`, `outcome`, and `unresolvedDefects`. If playback was unavailable, set `outcome` to `BLOCKED / UNREVIEWED`, use `null` for unobserved loop counts and identify the missing capability. Do not insert guessed values.

The current CLI review record is a hash-bound **human assertion**, not a video observer or verifier of these observations. Attach the actual temporal evidence report and explain the method in the `motion_contact` / `identity_stability` notes. A fresh CLI gate or `reviewed-draft` export does not override a blocked or rejected temporal art review.

## Arms and shoulders

Follow [source-specific arm ownership](arms-shoulders.md): never assume all hands show palms, do not duplicate one arm source for the other without evidence, and assign sleeve cap/socket pixels once. Inspect exterior matte as well as interior shoulder gaps, retain the connected shoulder–elbow–wrist chain and full sleeve/cuff boundary. Keep accepted leg alternation, garment coverage and timing during a local arm correction.
