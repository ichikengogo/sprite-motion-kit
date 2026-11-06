# Source-faithful arms, palms and shoulder connections

Use this checklist before generating or repairing an arm. It is per character, per view and per physical arm; no palm orientation, sleeve length or arm pose is a universal default. Use the existing authorization for the requested work. Do not require a separate user approval for every intermediate candidate.

## 1. Read the source before selecting the visible hand surface

Identify each physical arm and its screen/near-far mapping. Record whether the visible hand surface is **palm, dorsal/back of hand, edge, mixed through the motion, occluded or uncertain**, using actual source fingers, thumb side, knuckles and pose. A hand facing the viewer is not automatically a palm. If the view hides this evidence, record uncertainty; do not claim that a generated guess is original anatomy.

For held hands, preserve the actual contact and wrist orientation. For free arms, preserve the intended shoulder-led swing and natural forearm/wrist relationship. Decide whether the hand surface changes through that swing; do not simply flip one raster hand or force both hands to display palms.

### Review separate requirements separately

A correct palm surface does not establish a correct thumb side, and a correct thumb side does not establish the intended fist direction. For the actual forward-swing pose and then every other actual cel, inspect independently:

1. **Visible surface:** palm, dorsal, edge, mixed or genuinely hidden. Finger pads, knuckles and thumb overlap matter; color/alpha does not recognize them.
2. **Thumb-side facing:** which side or surface faces the body in this view. Do not narrow a request for a body-facing thumb side into a literal fingertip arrow. Preserve a natural closed grip rather than introducing a thumbs-up.
3. **Fist direction:** the fist mass relative to the wrist, forearm and body. A fist raised above its wrist is different from a forward punching silhouette. A desired upright key pose does not imply freezing the fist to world-up throughout the swing.
4. **Wrist and fingers:** one coherent forearm–wrist–palm transition, sensible curled fingers and cuff boundary, without an isolated thumb, duplicate finger or broken attachment.

Inspect the actual composited key pose at native size and enlarged **before** replicating a changed hand through the cycle. This is an internal art check, not an extra user permission gate. Then inspect both swing extremes, intermediate poses and partial occlusions. A neutral atlas may look right and rotate to the wrong visible surface in the intended pose. A two-dimensional mirror or rotation cannot reveal a missing palm or redraw wrist anatomy; author the required surface when needed and record it as inferred. Do not claim the hidden portion of an occluded hand was directly inspected.

Use the new `pose_review.py` worksheet for frame/physical-arm coverage and source freshness. It records authored intent and visual assertions; it does not recognize the hand surface. See the companion `docs/POSE_REVIEW.md` for commands and diagnostic limits.

## 2. Keep independent near/far arm sources

Retain a separate source or explicitly justified ownership region for each physical arm. Do not reuse a complete near arm as the far arm merely because both are similar: shoulder overlap, sleeve lighting, thumb side and visible hand surface can differ. Label anatomical left/right separately from screen-left/right and near/far; keep those identities through every pose.

When full-body generation causes identity drift, consider an immutable original head/torso, independently authored/articulated free arms, and coherent whole-pelvis/leg cels. This can preserve the face without freezing free arms. It is a representation choice, not an automatic fix. The generic package has existing manually registered mesh/projected rendering and drawn-cel assembly; it does not supply automatic shared-parts extraction. The newer layered_motion.py route renders explicitly authored layers and poses, not inferred anatomy. Route independently moving free arms through authored parts and manual rig/mesh ownership where viable, using provider-created source artwork when needed. The arm profile contract below guides those decisions; it does not perform them. Shared source pixels do not prove that joins or motion are correct; actual occlusion and shoulder motion still need review. Do not return to independently distorting waist, garment and thighs if that destroys their coherent shape.

## 3. Assign the sleeve cap and shoulder socket once

For each arm, annotate which source owns the rounded sleeve cap, shoulder seam, torso-side socket and any hidden overlap. Decide draw order explicitly. The cap should join the torso at the authored shoulder, with enough source-supported overlap during the swing. Avoid two complete caps stacked together, a rigid torso bump plus a moving duplicate cap, a floating round sleeve, or an exposed triangular hole.

Trace **shoulder → elbow → wrist → hand** as one connected chain. A wrist that follows the intended path does not excuse a detached shoulder or kinked elbow. Preserve source sleeve length and the entire cuff circumference; do not shorten the sleeve, expose extra skin, or enlarge the torso merely to conceal a seam. If overlap material exists in the original, adjust ownership/registration minimally. If missing surface must be drawn, use the image-editing tool and retain its inferred-region provenance, not code-painted filler.

## 4. Inspect both interior joins and exterior matte

Show each arm isolated and composited on cyan, magenta, black and checkerboard backgrounds. Inspect native detail and the intended small display size across all actual poses and the loop join.

- **Interior:** shoulder socket stays covered, cap does not duplicate, elbow/wrist remain connected, sleeve/cuff retains length and full boundary, held contacts stay attached.
- **Exterior:** no background-colored halo, white/gray wedge, old torso fragment, detached speck, rectangular matte or trimmed-away ink travels with the arm. Check alpha and RGB under partially transparent edge pixels, not only fully opaque areas. Never shave legitimate sleeve/hand contours to hide a matte.
- **Motion:** arm ownership and visible hand surface stay plausible throughout the swing; shoulder-led motion and free-arm opposition are retained. Physical legs still exchange support/recovery through both halves, with full garment coverage and the accepted foot trajectory.

## 5. Repair only what was requested

Freeze the accepted candidate and work in a sibling revision. For a palm or shoulder correction, preserve accepted pose order, frame timing, foot/pelvis path, body proportions, face/hair, garment length and other colors unless the repair genuinely requires a scoped change. Prefer source-faithful hand/sleeve patch ownership or local registration changes over full-body regeneration. Compare changed-pixel bounds and unaffected layers/frames, and report any unavoidable additional difference.

A missing real-time observation tool blocks **temporal quality certification**, not safe authorized fixes, source/alpha inspection, reproducibility checks or delivery of a clearly labeled candidate for user review. State exactly what was inspected and what remains UNREVIEWED; never claim playback observation from stills. Do not call known identity/scale jitter acceptable just because a local seam improved. User acceptance, candidate delivery and independent technical certification are distinct records.

## Character-neutral arm input worksheet

Complete this from the actual source; it is a human worksheet, not an automatic anatomy detector or a required renderer schema:

- View and facing:
- Physical arm owner; anatomical identity; screen side; near/far relationship:
- Original reference path/hash and independent arm source path/hash:
- Arm mode: free / held / absent; actual held contact if any:
- Visible hand surface and source evidence; uncertainty/occlusion:
- Shoulder, elbow, wrist and thumb-side observations in the source coordinate space:
- Sleeve length, cap/seam/cuff contour and preserved cloth/skin boundary:
- Cap owner, torso socket owner, overlap region, draw order and hidden/inferred pixels:
- Accepted motion/timing/identity baseline to preserve:
- Requested local change and allowed difference region:
- QA artifacts: isolated arm, contrasting-background composite, all-pose joins, changed-pixel report, temporal review status:

## Optional profile contract (`character_workflow.py`)

No new CLI command is required. Set `views[VIEW].armSurfaceSpec` to `null`/omit it when unrecorded, or supply `{ "arms": [...] }` with one record per independently identified arm. Unrecorded remains **unknown**, not automatically confirmed. Each arm record requires:

```json
{
  "physicalArmId": "source-arm-a",
  "visibleHandSurface": "source-dependent",
  "mode": "free",
  "pose": "Describe this physical arm's observed source pose and requested motion",
  "contacts": [],
  "shoulderBoundary": "Describe the actual shoulder/sleeve boundary and torso socket ownership",
  "elbowContinuity": "Describe how this source elbow remains connected",
  "wristContinuity": "Describe the source wrist/hand connection and thumb orientation",
  "occlusionExpectation": "Describe the near/far overlap and any unknown hidden pixels"
}
```

This is a character-neutral input pattern, not ready-to-confirm evidence. Replace descriptions from actual observation and add a separate record with a distinct stable ID for the other physical arm. `visibleHandSurface` accepts `palm`, `dorsal`, `edge`, `occluded` or `source-dependent`; choose the observed value, never a universal palm default. `mode` accepts `free`, `held` or `none` and must agree with the resolved per-view/global contact mode. Held mode requires nonempty `contacts`; free/none require `[]`. For absent arms, `arms: []` is permitted with resolved mode `none`. Duplicate physical IDs are invalid.

`plan` and `transition` carry `armSurfaceSpec` and an `armSurfaceReview` record with status `unrecorded` or `specified-not-visually-validated`, requirements and `automaticSemanticValidation: false`. The declared arm count is not fixed; inspect every arm actually present in the source, because a supplied list does not automatically prove complete coverage. All declarations remain **visually unverified**. Schema validation catches incomplete or contradictory declarations, not whether a palm or shoulder is actually drawn correctly. Keep independent source paths/hashes and masks in the worksheet/private project; this profile does not automatically segment or rig arms.

An arm may additionally include `handPoseIntent`, either `null`/omitted (unrecorded) or an object with four nonempty text fields: `thumbSide`, `fistDirection`, `wristAndFingers`, and `phaseContext`. Describe each from this character and intended poses, including uncertainty. There are no default directions. `plan` and `transition` pass the complete intent unchanged to the drawing request; changing it invalidates the prior intake fingerprint. This is an input contract, not evidence that any resulting hand meets it. Use the per-frame review worksheet for later observations.

## Read-only localized-repair audit

After rendering a sibling candidate, the generic `repair_audit.py` can check invariants:

```sh
python repair_audit.py --before work/baseline/frames --after work/candidate/frames --allowed-masks work/candidate/allowed-masks --out work/candidate/repair-audit.json --before-gif work/baseline/preview.gif --after-gif work/candidate/preview.gif
```

Supply matching `frame-*.png` files and same-sized per-frame grayscale (L) masks; nonzero means edits are allowed, zero means RGBA must remain identical. Define the legitimate repair region before judging the difference; a full-white mask cannot establish localization. The audit checks frame names/dimensions, out-of-region RGBA equality and optional GIF timing and repeat-loop metadata, and never awards visual acceptance. It does not align images, repaint pixels, infer motion trajectories or validate palm/shoulder anatomy. Check profile/pose diagnostics separately for unchanged motion, inspect actual joins, and retain real-time review status honestly.

## Local image-editing request

> Use the original and the specific arm source as identity and anatomy references. Correct only [HAND SURFACE / SLEEVE CAP / SHOULDER JOIN] for [PHYSICAL ARM] in [VIEW]. The source shows [OBSERVED SURFACE AND THUMB SIDE], with [UNCERTAINTY IF ANY]; do not force a palm view. Keep the accepted shoulder–elbow–wrist pose, free-arm swing or held contact, sleeve length/cuff circumference, torso/head identity, other colors and every unaffected body part unchanged. Preserve the cap’s source shape and its overlap behind/over [SOCKET OWNER]. Remove only confirmed exterior matte contamination, not legitimate contour ink. Return transparent artwork and identify any newly inferred hidden surface.
