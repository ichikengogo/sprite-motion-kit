# Explicit authored-layer route

`layered_motion.py` is a small reusable renderer for full-canvas transparent layers and explicitly authored per-frame joint chains. It preserves a shared head/body when those layers have no pose, with optional common translation. It does **not** extract parts, infer joints, draw missing surfaces, solve 3D rotation, simulate cloth or certify gait.

```sh
python layered_motion.py --demo output/layered
python layered_motion.py work/character/manifest.json output/rendered
```

The demo writes original geometric front, side-right and back fixtures, each with a manifest, layer PNGs, 12 output PNGs and a playable preview GIF. It samples phases `i / count`, not the duplicate terminal phase. The shapes are technical diagnostics, not a finished animation showcase. Both commands reject a nonempty output directory to avoid overwriting work. The authored-input command writes PNG frames; timing and a playable export must be supplied separately by the production workflow.

## Manifest v1

Required:

- `version: 1`
- `canvas: [width, height]`, positive integers
- `layers`: a nonempty list in default back-to-front order. Each has a unique `name` and `file`, a relative path to an RGBA image of exactly the canvas dimensions. Paths cannot escape the manifest directory.
- `frames`: explicit frame records. `poses` maps layer names to destination chains. `translation: [dx,dy]` optionally moves everything. `order` optionally lists every layer exactly once for that frame.

An articulated layer also has `rest: [[x,y], ...]`, at least two joints with strictly increasing rest Y, plus optional `root_blend` in source pixels. Destination chains must have the same count. `mesh_step` defaults to 8 pixels. Arbitrary canvases are supported; the old editor's fixed 384px rig schema is separate.

Within `root_blend` below the first joint, a smooth bounded weight mixes body translation with the posed chain. Below this band the limb owns its motion. Width offsets remain horizontal: this is a **2D strip warp**, not a rigid-surface or volume-conserving model. Folded/collapsed triangles are rejected. Out-of-canvas pixels are clipped, so inspect complete bounds before acceptance. Source artwork must already contain enough shoulder/hip/socket overlap; the renderer cannot invent it.

## Pose helpers, not automatic rigging

- `limb_phase(phase, owner, kind)` keeps physical left/right identity and opposite same-side arm/leg phase, independent of screen side.
- `project_forward(distance, view, depth_scale)` maps a physical forward displacement to a declared side/front/back screen convention. Front and back use opposite depth signs. This is a calibrated proxy; actual drawings still need visible depth and occlusion review.
- `support_height_offset(supports)` computes a weighted vertical offset using **only supplied stance legs**, with their hip/ankle, two lengths, desired knee flex and optional weight. Swing legs must not be supplied. Impossible horizontal reach is rejected. This helper is opt-in and does not run automatically during rendering; it is not a foot locker.

`fit_periodic_support_height(samples, harmonics=2)` optionally fits a low-order Fourier height curve from `[{"phase": p, "supports": [...]}, ...]`. It returns a callable periodic fit plus diagnostics for vertical RMS/max/per-support residuals, reach margins/errors at supplied samples, matrix rank and conditioning. Simultaneous stance constraints remain separate and weighted. Unreachable, insufficient and rank-deficient inputs are rejected. This is a smooth approximation: it does not enforce exact contact or check unsampled reach, and it is not automatically connected to rendering. Recheck a dense full-cycle pose sequence before adopting it.

Do not mistake an inferred hidden hip for an observed source joint. Inspect both contact extremes relative to the body. Verify support-height curves and every exchange, not just four keys, and retain intended foot tracks rather than blindly preserving obsolete reach clamps.

Use `production_audit.py` for explicit landmark timing/loop diagnostics and `repair_audit.py` for scoped pixel invariants. Complete semantic ownership, sleeve/garment volume, actual motion direction and 1x observation remain human review tasks.
