# Local repairs without losing the whole component

This workflow extends [pose review](POSE_REVIEW.md) and [dash reproduction](DASH_REPRODUCTION.md). The new diagnostics compare explicitly authored pixels and masks. They do not recognize faces, hands, hair, accessories or valid negative space, and they do not grant visual or temporal acceptance.

## Lessons and independent checks

1. **A stable face can still face the wrong way.** Inspect actual yaw, gaze, jaw/neck continuity and hair identity before freezing a head. Stabilize the intended shared face and upper-body landmarks at one source scale, preserving declared whole-body bob. Compare separate head, collar, chest and accessory cores after only that declared translation. Do not fit each frame's bounds or align away unexpected horizontal drift. Moving arms may hide the torso, so a whole-torso equality claim is usually too broad. A matching reference is not proof that the reference is front-facing.
2. **White paint and a transparent hole are different failures.** Inspect native RGBA on light, dark and saturated backgrounds. A fully transparent pixel reveals the background. An opaque pale patch does not. A backing layer can fill the former but cannot repair the latter without changing its visible owner. Diagnose alpha separately from color and intended material. White cloth or a highlight is not automatically wrong. For an actual hand repaint, retain the phase-specific cuff, wrist, fingers and hand-surface intent from `pose_review.py`.
3. **Long hair is a surface with ownership, not permission to fill every opening.** Author the missing hair layer from the actual reference, retain its provenance, and place it behind the appropriate hand/sleeve/body. Preserve genuine negative space and the complete silhouette. For a backing-only repair, every originally opaque foreground pixel must remain equal, alpha must not decrease, and changes must stay inside the declared reveal scope. Partially transparent edges can legitimately change when composited, so inspect those separately. These invariants alone do not establish that the expected hair actually appears.
4. **A fixed buckle does not establish a continuous strap.** Inspect the entire band from attachment through hardware to its terminal contour, in every actual cel, with one fixed crop size. Check the whole visible component as well as small position cores. Use explicit per-frame foreground masks where an arm genuinely hides it. Then check the foreground arm/hand independently: an underlay-only check can still pass when the strap has incorrectly been painted over the hand. Fully occluded regions are unmeasured, not passed.
5. **A connected sleeve can hide a missing fist.** Compare each physical hand through both halves of the cycle, especially the extended/retracted phases. Track the complete hand mass, wrist connection and silhouette, not only the fingertip or bounding box. A borrowed/mirrored source is a construction, not automatic proof of correct anatomy, thumb orientation or surface. Keep that provenance and reinspect the actual composed pose.
6. **Identify the exact tip before trimming it.** A pointed upper join and an intentional lower strap endpoint are different targets. Freeze the immediately preceding accepted export, locate the requested defect against the actual image, and use a narrow per-frame allowed mask. Use `repair_audit.py` to demonstrate that unaffected phases and all pixels outside that scope remain equal. Recheck the complete strap and arm occlusion afterward, not only the small edited crop.

These are source-specific review decisions. None of the coordinates, colors, thresholds, bob or repair sizes in the geometric tests are character presets.

## Reproduce the diagnostic failure cases

```sh
python continuity_audit.py demo output/continuity-example
python -m unittest discover -s tests -p test_continuity_audit.py -v
```

The demo requires a new directory. It creates original code-drawn shapes, binary masks, and three candidate PNGs: a correctly occluded component, a missing lower component, and an opaque repaint. The JSON report distinguishes transparent loss from opaque color changes. Its success means the deliberate diagnostic outcomes were reproduced, not that an animation looks good. No production artwork, external image service or saved private project is used.

The tests additionally cover a stable translated core, lateral drift, wrong foreground draw order, complete occlusion, a disappearing hand region, backing-only preservation, meaningful negative space, and a localized tip correction with unchanged phases. Both good and bad cases are necessary: an equality test against a small buckle alone demonstrably misses a removed lower band.

## Python API

`registered_region(reference, candidate, region_mask, offset=(0, 0), occluder_mask=None)` compares PIL still images on the same canvas. `region_mask` is a binary L/1 image in reference coordinates and must select nonempty, fully opaque reference pixels. `offset` is the explicitly declared integer reference-to-candidate translation. The optional binary `occluder_mask` is in candidate coordinates. Clipping and non-integer translations are rejected rather than silently hidden; no automatic registration or rescaling occurs.

The report records reference, visible and occluded counts; missing transparent pixels; partial-alpha pixels; changed opaque pixels; and `matches`. `matches` is null when every selected pixel is occluded. Mask all fully opaque component pixels needed for the claim, not just a convenient core. Antialiased edges, translucency and newly authored poses require their own composite/visual review. A per-pose reference is allowed, but it must be independently justified rather than copied from the candidate to manufacture a pass.

`backing_preservation(before, after, allowed_reveal_mask)` checks unchanged opaque foreground, unchanged outside-scope RGBA, and nondecreasing alpha. `invariantsPass` does not mean the hole has been filled: an unchanged candidate can satisfy preservation. Pair it with the complete expected component check and actual image inspection. Keep the reveal mask meaningful; an all-canvas mask provides no locality guarantee.

Both APIs return decoded-array hashes bound to shape and dtype, including masks, rather than encoded-file SHA-256. Store their reports alongside a source-pinned `dash_project.py` or `pose_review.py` manifest when byte-level replay and review freshness are needed. The APIs neither authenticate a reviewer nor update existing review status. They do not infer frame order, durations, source intent or mask coverage; iterate over the explicit list of **every actual authored cel**, with its own expected layer, translation and occlusion.

## Preserve the correction boundary and evidence

- Freeze source images, generated or constructed layers, the actual previous export, masks, assembly code, frame order and holds. Pin hashes. AI regeneration is not deterministic replay; replay from the frozen authored layers.
- Rebuild in a clean output directory, compare every PNG and encoded preview, and verify unaffected directions, protected lower rows and timing. Keep existing pose/production review tools rather than duplicating their schemas.
- Inspect full bodies and fixed-size tracked crops on contrasting backgrounds, then observe the exact output at normal speed at native and intended small size, including repeated loops and the last-to-first join. Decoding video, static sheets and byte equality do not establish continuous viewing.
- Keep structural checks, static findings, temporal observation, user acceptance and in-game integration separate. These diagnostics always report `visualApproval: false` and `temporalReview: UNREVIEWED`.

For public changes, commit only generalized code, original synthetic tests and the procedure. Keep private references, character names, production coordinates, cels, comparison media, upload receipts and conversation records outside the repository.
