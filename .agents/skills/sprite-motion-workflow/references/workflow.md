# Runnable registered-rig three-view workflow

For a **new unknown character**, start with [character intake and planning](character-workflow.md). This file documents the existing manual rig route, not a substitute for source-specific profiling or an automatic image generator.

For coherent drawn-cel side walks, use [the separate drawn-cel workflow](drawn-cel.md) and `drawn_cel.py`. The commands below operate on registered three-view rigs, not drawn-cel projects. Repeated rejected cloth/hip deformation is a reason to choose the drawn-cel route, not keep adding rig options.

## Engine and local setup
Run from the companion `sprite-motion-lab` root, Python 3.10+. A standalone skill ZIP is **not executable by itself**: obtain the matching engine package with `workflow.py`, `server.py`, modules, browser assets and `requirements.txt`. Do not copy only the two entrypoints. Use a project-local environment, not global installation:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python workflow.py --help
python workflow.py init --front /path/front.png --side /path/side.png --back /path/back.png --out work/new-character
python workflow.py status work/new-character/manifest.json
```

`init` requires three nonempty transparent PNGs and a new output directory; it preserves bytes and hashes. It does **not** remove backgrounds, segment parts, recognize the character or validate cross-view identity. Inspect originals together **before segmentation**. Stop for mismatched faces/hair/costume/accessories or uncertain orientation; obtain corrected inputs or explicit acceptance of intentional variation. Save the comparison and decision as real identity evidence, then record it before editor segmentation:

```sh
python workflow.py identity work/new-character/manifest.json --evidence review/three-originals.png --note 'Compared face where visible, hair, costume, accessories, shoes and neutral proportions across all three originals; same character confirmed'
```

`identity` records a manual assertion bound to all three intake hashes, not an automatic recognition result. It is required before `bind` and retained when rebinding. Do not attest until the comparison has actually been performed. Never flip the side image to substitute for front or back.

## Manual editor handoff

```sh
python server.py
```

Open http://127.0.0.1:8765 on the machine running the server; another computer does not automatically have access. Load each original in its matching view. 「候補を作る」 is only a low-confidence geometric starting point. Edit masks, start/end joints and ordering; inspect all 12 slots (hands included with forearms, shoes separate). Screen-left/right are not universal anatomical labels. Confirm every slot only after checking ownership, contours and occlusion. Keep one coherent shared pelvis/garment rather than two overlapping complete shorts.

Where anatomy is hidden, the engine cannot reconstruct it. Supply independently reviewed full-canvas replacement layers, with permission for any generated artwork; identify inferred pixels. Explicitly distinguish original-space from normalized 384-canvas coordinates. Keep the embedded original alongside normalized source; do not replace it with another character or a cosmetically changed face. Save JSON using 「作業を保存」 and reload using 「再開」.

Front/back require a manually registered `projectedWalk` rig, all required confirmed parts and valid nonoverlapping source ownership; merely loading the PNG does not complete this. The current projected renderer requires normalized `neutralHeight=317`, `ground=349`, `centerX=192` on a 384 canvas; these are an engine coordinate contract, not a prescription for original body proportions. It also bounds source joint positions, so register/validate deliberately. Read companion `docs/PROJECTED_FRONT_BACK.md`, `docs/ARCHITECTURE.md` and validators for the actual fields and currently supported registration domain. This projection is not full 3D, automatic occlusion solving, clothing physics or unseen shoe-sole synthesis. If a new character cannot fit the supported registration domain, stop and report the required engine/rig adaptation rather than forcing example coordinates.

Side uses its own rig. `walkStyle` offers cautious/purposeful/wide-stable/simple; `simple` is side-only (8 keys, 1 second). Do not swap profiles after approval without re-review. Front/back dash is unsupported by this workflow; side dash remains a separate action requiring separate review.

For side originals whose hands grip backpack straps or another torso-fixed item, explicitly set `rig.armPose: "held-source"` to retain the authored bent arms during walking. Both upper arms and forearms follow the torso transform using their own source pivots and angles; this overrides walk arm swing (`armMotion` / `armSwingScale`), not leg motion. It is side-view only, has no dedicated UI toggle, and does not affect dash or neutral rendering. Omission or `"legacy"` preserves existing behavior. Zero swing alone is not a substitute because it does not retain the source elbow pose. Verify shoulder/elbow/wrist registration, source-pixel ownership and hand/strap attachment through all keys and intermediates; this option does not reconstruct hidden surfaces or automatically validate the grip.

When a side thigh/shin mesh needs both `waistAttachment` and `walkAnkleDepth`, optional `waistAttachment.ankleContinuity: true` lets the existing distal shoe-attachment mapping run after waist attachment. Omission/false retains the legacy early return byte-for-byte. This combines registered transforms; it does not repaint collars or prove heel containment. Review the actual calf/sock and rigid shoe contours through every phase before recording the heel gate.

```sh
python workflow.py bind work/new-character/manifest.json saved-project.json
```

`bind` validates the saved three-view setup and checks source pixel correspondence against intake. Pixel equality **does not establish that all three images depict the same character**. Manual identity and normalized-source/replacement provenance review is still required. Rebinding invalidates prior review records; changed project or archived evidence bytes require fresh review. Evidence is copied into portable `evidence/<sha>.<suffix>` under the manifest directory. Keep those archived copies unchanged; edits to the original external evidence file do not change the archived record.

## First three-view draft
For **each** view, record `source_correspondence` and `proportions` after performing those reviews. Example for front (repeat with `--view side` and `--view back`, using each view's real evidence):

```sh
python workflow.py attest work/new-character/manifest.json --view front --action walk --gate source_correspondence --evidence review/front-source.png --note 'Compared all originals for identity before segmentation; front face/costume match, original registration verified, inferred regions documented'
python workflow.py attest work/new-character/manifest.json --view front --action walk --gate proportions --evidence review/front-neutral.png --note 'Checked source landmarks and approved neutral reference at fixed scale; no per-frame bbox fitting'
python workflow.py export work/new-character/manifest.json --view all --action walk --mode draft --out work/walk-draft
```

Evidence paths must exist and notes must describe work actually performed. Do not run the example attestations blindly, create dummy evidence, or automatically attest after tests. These are human assertions, not image-classifier results.

The all-view directory contains `front/`, `side/`, `back/` and a top-level `summary.json`. Each view contains transparent `sheet.png`, individual frames, `animation.json`, `preview.gif`, contrasting-background QA sheets, 24 intermediate transparent frames, intermediate QA and `review.json`. The root `comparison.gif` plays front/side/back together. Both GIF types use opaque light gray (`#dddddd`) for viewing, not as transparent game assets. They follow actual metadata timing; GIF centisecond limits round cumulative boundaries (8 keys over 1 second alternate 120/130 ms, while PNG/JSON retains exact 125 ms). When views have different key counts, comparison uses their combined time boundaries and holds the active frame, not a frame-index pairing. Transparency belongs to animation assets; QA sheets intentionally use visible backgrounds. Export refuses an existing output directory. Use the actual metadata for frame count, period and pivot.

## Full-cycle review and reviewed draft
Read `quality.md`. Inspect each key and all intermediate phases, including normal-color full-body comparisons at native and game size. Required full gates, independently for every view/action:

`source_correspondence ownership landmarks hidden_parts proportions outlines cloth_coverage heels whole_cycle`

Record each completed gate using `attest --view VIEW --action walk --gate GATE --evidence FILE --note TEXT`. Export does not create these judgments for you.

```sh
python workflow.py status work/new-character/manifest.json
python workflow.py export work/new-character/manifest.json --view all --action walk --mode reviewed-draft --out work/walk-reviewed-draft
```

`draft` requires source-correspondence and proportions records; `reviewed-draft` requires all nine gates per selected view. Both remain `draft: true`, `approved: false`: reviewed-draft means recorded evidence, not automatic final acceptance. Reinspect the exported files themselves and report remaining defects. The export uses the editor/API rendering path, including saved replacement/garment layers. Basic `cli.py --image ... --rig ...` is not a substitute for advanced saved projects because it does not load all saved layers.

## Gait, proportions and optional front surface tuning
Set the character's own head/chin/shoulder/hip/knee/ankle/sole and garment landmarks. Separate bone length, pose foreshortening, cloth coverage and surface deformation. Use one neutral-height-derived constant global scale; retain bobbing, shoe aspect and intentional body proportions. Never copy the private example's leg multiplier, target height, ground or width settings as universal defaults.

Review contact/down/passing/up; oppose each arm to its same-side advancing leg and check visible excursion, not just formula phase. Increase stride and arm motion only within reachable/validated settings, reviewing foot clearance, support and full silhouettes after each change. Do not shrink stride merely to conceal seam defects.

For manually registered front/back `rig.projectedWalk` only: `armAmplitude` (0..10, default 6), `armSpread` (0..4, default 2), and optional `armFadeDepth` (20..40 px) tune projected arms and distal influence. They are not the side rig's `armSwingScale`. Stronger motion may expose previously hidden contour/cloth errors. An opt-in `legInterpolation: "linear"` linearly maps hip/knee/ankle endpoint displacement, which can avoid a flattened shin in some front registrations. It changes intervening cloth/skin mapping, not endpoint foot paths, and is **not** a universal volume fix. Omission retains legacy smooth mapping. Compare both on the new source, inspect knees/shins/ankles and dense active triangles, and do not apply private amplitude or stride selections by default.

### Optional source-registered hips and cutout hems

For side/simple walk only, `walkHipRegistration: "source"` retains each manually registered hip rather than applying the legacy mean-x simplification. Omission (or `legacy-centered`) is unchanged. Register the new character's own landmarks first; this does not change source bone lengths or authored foot-path targets, but corrected hip placement can change support correction, IK knees and recovery poses. Never use the option as an automatic anatomy guess.

For original cutout cloth panels with `walkGarment.hemConnection`, `walkGarment.sourceHemMode: "preserve-x"` keeps each source hem sample's original x when attaching it to the leg mesh. It avoids a second source-box-to-hem-width compression of an existing silhouette. Omission (`registered-width`) retains the existing authored rectangular-panel mapping. Sparse source-cutout corners may be empty: this option checks finite mapping coordinates and actual occupied mesh triangles, rather than treating the full source-box quad as filled cloth. Occupied folds/collapse still stop rendering. This is not a new garment raster, missing-surface synthesis or universal seam fix.

Both options require source-specific ownership and full-cycle visual checks of a shared stable pelvis, moving leg openings, cuffs, knees and ankles. Inspect all keys and24 intermediate phases at native and128 size on contrasting backgrounds; do not transfer private calibration values. Default renders and dash are unchanged.

## Verification and distribution

```sh
python -m unittest discover -s tests
node tests/test_playback.cjs
```

Tests check implementation, not character quality. Reopen saved JSON and rerender to verify reproducibility; inspect RGBA/metadata and evidence freshness. Keep originals, embedded-image saved JSON, inferred private layers and review screenshots in a private workspace. Generic source/skill packages must exclude them. No global install, Mac deployment, external upload, publication or license decision is implied by this workflow.

### Optional source cuff normals (side/simple walk)

A `jointMeshes[]` thigh/shin pair with `walkContour: "centerline"` may opt into
`walkCuffNormal: {"startY": ..., "endY": ...}`. Register these positive, increasing
Y coordinates (at most384) on that character's upright source material: the
cross-section normal smoothly follows the shin through this band, reaching the
shin normal at `endY`. This changes sampled material geometry only, not the
hip/knee/ankle trajectories, centerline, contacts, or source RGB. It is walk-only;
omission preserves the existing mapping. Values are not transferable anatomy
presets. This is not fabric synthesis or automatic clothing recognition.

Inspect the **entire original garment boundary and outer cloth coverage**, not
just knee-center alignment or opaque alpha. Compare source contours and all8 keys
plus24 phases at native/128px on contrasting backgrounds; check skin exposure,
cloth continuity, active mesh folds/compression, and foot continuity. A fully
opaque image or a centerline inside black material can still omit intended cloth
on the outside of a bent knee. Reject that semantic loss.
