# Reproducible authored dash repairs

This route preserves general production lessons as explicit algorithms, source-pinned projects and synthetic regression tests. It does not include production artwork, character measurements, accepted private outputs, or a pretrained model. It does not turn a walk into a run by increasing playback speed.

## Run the complete synthetic example

```sh
python dash_project.py demo output/dash-example
python dash_project.py verify output/dash-example/project.json output/dash-example/rendered
```

Use a new output directory. The example draws original geometric sources, records their hashes, applies authored registration, writes all actual RGBA cels plus native/small GIFs and a report, then can be reproduced exactly. It is a technical fixture, not evidence of attractive motion on an unseen character.

The lower-level helpers also have their own synthetic demo:

```sh
python dash_registration.py --demo output/dash-helpers
```

No new dependency is needed beyond NumPy and Pillow. The monotone cubic interpolator is implemented locally; SciPy, external image services and ffmpeg are not required.

## Choose the representation before repairing

- If separate arms plus a rigid torso repeatedly open shoulder slits, a coherent neck-down body cel with one immutable head may be simpler. Changing representation still needs actual shoulder, clothing and motion review.
- Keep independently authored left/right arms when their poses and hidden surfaces cannot be obtained by plausible deformation. A width adjustment cannot fix a fundamentally wrong pose.
- Give straps, bags, cuffs and hands one deliberate visible owner. New arm artwork must not add another copy of a strap already owned by the torso.
- Retain one artwork scale across the cycle. Register a waistband, neck or support sole, rather than normalizing every frame's bounding box.

Use existing cel/layered routes for animation that does not need axis stabilization. The new project is an optional repair route, not a replacement for every character's gait.

## Shared axis without resampling the face

For each neck-down cel, author three source landmarks in order: neck, central chest landmark, waist. Supply the three target landmarks and the first row of a protected lower region.

`align_body_axis(body, source_landmarks, target_landmarks, lock_y)` builds two shape-preserving cubic maps:

1. Target landmark Y to original landmark Y, with the protected boundary as an identity endpoint.
2. Original landmark Y to original body-axis X, approaching the target axis at the protected boundary.

For destination `(x,y)`, sample the original Y from the first map, then offset X by the original axis minus the target axis. Above the first landmark, use translation; at and below the boundary, use identity. After image interpolation, paste the protected lower rows back exactly. Source/target Y values must be finite, strictly ordered and above the boundary; target X values must share one axis. A fixed axis and repeated half-cycle bob are **style choices**, not automatic anatomy corrections or universal running rules.

`translate_shared_layer(head, [dx,dy])` uses integer-only translation with no resampling. It avoids repeatedly filtering or redrawing the face. Use the same original head every time, and keep its neck attachment coherent. Integer translation does not repair an incorrect head pose. The canvas clips out-of-bounds artwork; inspect alpha bounds and the export's canvas warnings; do not infer that unchanged scale means nothing was cropped.

The high-level project rejects a composite whose shared head changes protected lower rows. It reports source/target landmark ranges, index-half differences, duration-matched half-cycle differences when applicable, and adjacent steps including last→first. Reduced numbers do not prove that the actual body, hood or garment looks stable.

## Extend the arm shaft while preserving the hand

`shaft_hand_mapping(start, wrist, length_scale=..., width_scale=..., target_start=..., rotation_radians=...)` separates the shaft from the distal hand. Projection onto the authored limb axis makes it applicable to tilted source arms.

Within the start-to-wrist interval, added length is a ramp. At and beyond the wrist, the added length is a constant translation, followed by the common rigid rotation. The hand is not lengthened merely because the shaft is longer. Width changes blend back to the original hand width at the wrist. This helper is a point mapping, not an integrated textured-arm renderer. Its rigid-hand guarantee requires every intended hand point to be at or beyond the authored wrist plane; use a separately owned rigid hand layer when the silhouette crosses that plane. It does not identify the wrist from skin color or produce missing fingers.

For a two-link arm, adjust upper-arm reach and the elbow-to-wrist shaft separately while keeping the shoulder and intended swing/flex phases. Review the entire shoulder–elbow–wrist chain. A bent arm can look short because its elbow is near the torso or the fist is occluded; diagnose anatomical length, silhouette, width and depth separately before changing hand size. Rotated bounding boxes are not reliable hand-scale measurements.

## Widen around the actual centerline

`widen_rows(image, centerline_x, root_y=..., blend_end_y=..., width_scale=...)` accepts an explicit per-row centerline. Rows at or above the root remain unchanged; a smooth transition introduces width below it. This changes width around the arm's path, rather than scaling shoulder-to-hand displacement.

Supply landmarks or masks from the actual artwork. Do not use a universal skin-color threshold to locate a wrist. The basic helper has one width control; independently authored sleeve/hand regions can be prepared and reviewed separately when they need different corrections. It is not a volume-conserving simulation.

## Project contract

A project is JSON with:

- `schema: "dash-registration-project/1"`
- `view`: `front`, `side` or `back`; a separate project per actual view.
- `canvas`: `[width,height]`, both 1–4096.
- `sharedHead`: relative path to an RGBA PNG on that canvas.
- `durationsMs`: one positive integer multiple of 10 per actual authored cel, at most 60000ms each and 655350ms for the entire cycle (including possible GIF hold coalescing).
- `smallHeight`: optional intended small preview height, default 128.
- `frames`: 4–256 records. Each specifies `body` (relative RGBA PNG), `sourceLandmarks` and `targetLandmarks` (exactly three `[x,y]` pairs), `headTranslation` (two integers) and `lockY`.
- `sourcePins`: file SHA-256 values, written only when explicitly pinned after inspecting the source.

All assets must stay within the project directory. The canvas is shared; the tool does not infer landmarks, split a head from a body, infer missing views, or change the source files.

```sh
python dash_project.py pin work/character/project.json
python dash_project.py render work/character/project.json output/character-dash
python dash_project.py verify work/character/project.json output/character-dash
```

Pinning is a provenance operation, not approval of identity, rights, anatomy or motion. A source edit invalidates its pin until deliberately inspected and repinned. Export directories are immutable; use a sibling directory for a revision.

## What the checks establish

- Ordered, finite, shape-preserving registration inputs and exact protected lower rows.
- Reused head pixels with integer-only translation, subject to declared canvas clipping.
- Rigid distal-hand geometry for shaft length changes; independent shoulder-root protection for width changes.
- Actual cel count, source hashes, GIF durations, cycle seam metrics and byte-exact clean regeneration in the tested environment.
- Source and output tampering produce explicit failures; a report containing false booleans is not a passing verification.

Rendered PNGs retain every authored cel. GIF encoders can merge identical adjacent cels while preserving total holds, so reports distinguish authored and encoded timing. A video encoded at 60fps from eight cels still has eight drawings. This CLI exports GIF/PNG, not MP4, and does not create new inbetweens.

## What remains a human decision

Inspect source and candidate at the same fixed scale. Check each sleeve, hand, calf and shoe independently, coherent shoulder/neck joins, strap ownership, hem/hood flicker, support/recovery and visible opposition in both half-cycles. Inspect normal-color output before numeric summaries.

Observe the exact candidate at normal speed and both intended sizes before describing temporal quality as reviewed. Exporting a playable GIF, decoding timestamps or examining a contact sheet is not this observation. Keep structural results, static review, actual playback review, user acceptance and engine integration as separate statuses. New exports are always `draft`, with `visualApproval: false` and `temporalReview: "UNREVIEWED"`.
