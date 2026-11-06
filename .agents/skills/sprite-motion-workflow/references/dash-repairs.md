# Reproducible dash repairs

Use `dash_project.py` in the companion toolkit for explicitly registered neck-down cels plus one immutable head. Read `docs/DASH_REPRODUCTION.md` for the exact schema and helper APIs. Start with `python dash_project.py demo output/dash-example` and verify it with `python dash_project.py verify output/dash-example/project.json output/dash-example/rendered`. The generated shapes are technical fixtures, not production art.

For new character artwork, identify actual neck, central chest and waist landmarks, choose a source-appropriate target axis/bob, and declare a protected lower boundary. Keep one source scale. `pin`, `render` and `verify` record the original PNG hashes, reproduce every real cel, native/small GIF timing and protected pixels. Do not reuse demonstration coordinates or another character's proportions. A fixed axis and symmetric half-cycle bob are optional stylistic constraints, not a rule for every dash.

Keep the shared head on integer translations when that representation is appropriate, avoiding per-frame face filtering/redraw. Registration of body landmarks does not eliminate authored garment-shape differences or establish correct support. If separate arms plus a rigid torso produce repeated shoulder slits, consider coherent neck-down body cels; if arm poses cannot be plausibly warped, author them independently. Do not use arbitrary flat filler to hide missing anatomy. Assign straps, hands and garment surfaces one clear visible owner.

Use `shaft_hand_mapping` to extend the shaft without lengthening the hand beyond the wrist. Upper-arm reach, forearm length, sleeve width and hand scale are different decisions. Tilted limbs need axis projection, not a universal vertical rule. Rotated bounding boxes do not measure hand size reliably. Bent elbows and torso occlusion can make an unchanged hand look too small.

Use authored per-row centerlines with `widen_rows` to change width without pushing the whole arm path away from the shoulder. Protect the cap/root and inspect full elbow/cuff contours. Avoid skin-color thresholds as a character-neutral wrist detector. Source-hidden material and unsupported poses still need authored imagery.

Check protected rows/masks, source hashes, actual cel count, durations, last→first steps, bilateral symmetry only when intended, and clean regeneration. Inspect each sleeve, fist, calf and shoe at fixed scale to catch unintended size changes. A report of a false check is not a successful test; fail explicitly.

An eight-cel loop encoded at 60fps still has eight drawings. GIF/video hold quantization can differ; use actual timing metadata for comparisons and never call held frames new inbetweens. The CLI writes GIF/PNG, not MP4.

Playable exports, numeric improvements and static sheets do not establish continuous observation. Preserve separate structural, static, real-time, user-acceptance and integration statuses. Apply [quality.md](quality.md): if the exact output was not observed at normal speed, temporal quality stays UNREVIEWED. Deliver a clearly labeled candidate without claiming automatic naturalness.
