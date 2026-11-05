# Coherent drawn-cel walk: assembly and review

For new characters, start at [character intake/planning](CHARACTER_WORKFLOW.md). This is the downstream assembly route after actual source-specific artwork and registration exist; a template alone does not generate a character.

This is a separate, deterministic assembly route, not a new mesh preset. Standard coherent full cels use `character_workflow.py register-cels` with no per-pose coordinate entry; the source waist/overlap instructions below concern the optional advanced shared-upper/lower representation. Use it when a source pose hides essential surfaces, cloth must remain a coherent tube, or repeated joint/waist fixes are changing the design. Do not keep stacking seam patches on a rejected motion. Existing mesh/projected workflows remain available for suitable material and preserve their defaults; their numeric passes do not establish that a rejected walk is acceptable.

The per-view assembly entrypoint is `drawn_cel.py`; `character_workflow.py` coordinates original intake, profile, requests and all-view binding/rendering. The standalone skill contains instructions only. No private example artwork or coordinates belong in the generic engine or skill. A saved character project must carry its own sources, registrations, ownership and evidence.

## 1. Intake and choose the representation

- Inspect the actual original, including alpha on contrasting backgrounds. Preserve its bytes and hash; compare face/head ratio, source hairstyle, clothes, garment length, shoe shape, accessories and orientation. A dark RGB background underneath zero alpha is not an opaque background.
- Record screen-facing direction separately from anatomical left/right and **near/far leg identity**. A far leg remains the far leg when it advances. Identify occluded surfaces and disclose generated completion.
- Freeze the original proportion/reference scale, ground and intended cycle duration. Do not inherit another character's coordinates, leg multiplier or stride. Do not normalize every frame's bounding box to one height: that destroys bob and changes anatomy.
- Decide whether torso/face/hair/source accessories and authored hand pose can be one common source cel. For strap-holding poses this removes identity flicker while maintaining grip. It is not permission to redraw or independently wiggle those features. If upper-body rotation is required, review that explicit motion rather than silently introducing it.

## 2. Establish coherent whole lower-body poses before assembly

Create contact → down → passing → up as a unified pelvis, two thighs, source-appropriate garment, calves and shoes. Preserve the actual garment length (for example, knee-length capri); do not impose that example on another costume. Use an authorized drawing or image-editing workflow for raster redraws, with the original as identity reference. Assembly code should not silently substitute crude filler for missing authored skin or cloth. Keep rejected attempts separate. Avoid using a previously warped/rejected result as the identity reference.

| Phase | Support and recovery that must be visible |
|---|---|
| Contact | Advancing heel reaches ground; opposite leg trails toward toe support. |
| Down | Planted foot takes weight, knee flexes and pelvis compresses modestly. Not another contact drawing. |
| Passing | Support leg carries body; recovering foot clears near support ankle/lower calf and moves **forward under pelvis**. No high backward kick. |
| Up | Support heel rises into forefoot push-off; recovery leg advances low ahead. Not high-knee marching or a repeated wide stance. |

Compare original and poses at a common reference scale and ground. Judge thigh initiation at the hip and a connected seat/waist first, not ankle seams alone. Confirm direction with the user when the approach is new or specifically requested; do not invent an extra approval gate for already authorized work. Direction approval is not final animation approval.

## 3. Build both half-cycles, not four poses twice

Complete the opposite half-cycle with **near/far support and recovery roles exchanged**. Make foreground overlap explicit in the prompt and saved phase metadata. A mirrored label or a slightly different shoe color is not a role exchange. In contact/down pairs separated by half a cycle, trace the same physical leg through its thigh, cuff, shin and shoe. In passing/up it must recover from rear to front, not jump back to the old rear placement.

Start with eight actual cels; add one or two targeted intermediate cels where support-foot travel or recovery makes a large pose jump. Keep accepted phases rather than regenerating the entire sheet. A ten-cel project has ten real drawings, not 24 interpolated poses. Do not crossfade, duplicate holds or call sampled playback timestamps newly synthesized anatomy.

For a failed interval, reference the original and **both adjacent actual cels together**, not only a single target phase description. Preserve character scale, source-specific arm condition and physical foot roles. Use the [transition request and temporal art-gate procedure](CHARACTER_WORKFLOW.md); support-foot marker travel divided by actual interval time and face/hair/torso sequences are human QA, not automatic quality scores. Timing-only changes do not supply missing drawings.

## 4. Source ownership and waist overlap

Register complete lower-body cels with uniform scale and translation, grounded in each source's actual waist/sole landmarks. These are recorded character-specific placements, not per-frame automatic bbox fits. Preserve shoe aspect, leg lengths and intended pelvis movement.

The shared upper cel should overlap the **original source material beneath the hem**, not amputate the seat at a convenient horizontal row. Before clipping:

1. Inspect each source's curved shirt hem and rear seat at native scale.
2. Show retained/discarded source pixels and common upper cel separately.
3. Ensure the lower cel reaches behind the hem across both front and rear waist edges. A rear horizontal shelf outside the torso can look detached even if the alpha components touch.
4. If the source already contains the needed connection, restore that source-owned cloth using a small explicit ownership polygon behind the unchanged assembly. Do not fill the gap with an arbitrary opaque rectangle or redraw the whole hip. Record the polygon, source hash and actual output difference bounds.
5. If material truly does not exist, use a localized drawing or image edit and retain the inferred-region provenance. A restored original region and generated cloth are different claims.

Retain original curved cuffs/ink and **the full circumference of both garment legs**. At maximum lift, the actual garment must retain its source-appropriate hem and silhouette on the outer side as well as the centerline; for capri this includes the full knee cuff, while shorts, trousers, skirts and bare legs require different boundaries. A diagonal triangular flap exposing skin up the thigh is garment loss, even if every pixel is opaque, every joint is reachable and every mesh triangle is non-inverted.

## 5. Assemble, inspect, and keep claims separate

Use `drawn_cel.py` for assembly and portable source/evidence handling. Follow the exact CLI contract below. Validation renders the registered cels and checks structure, bounds, hashes, declared phase relationships, repeated half-cycles and configured alpha coverage probes; it cannot recognize natural gait, identity or garment semantics. Reviewed-draft means evidence has been recorded, **not** automatic aesthetic approval.

Inspect all actual exported RGBA frames, native and 128px sheets, normal color and cyan/magenta/black backgrounds, plus actual timed playback and the last→first transition. Reviewers should see images before numeric pass claims.

Required decisions:
- **Identity/common upper:** face, hair, bag and hand/strap attachment do not flicker. Shared-source identity is verifiable by source/transform, but whole composition still needs visual review.
- **Leg ownership/phase:** opposite half-cycle roles genuinely exchange; recovery travels forward; no duplicated leg, reversing foot or hidden extra shoe.
- **Waist/seat:** no horizontal cut, detached rear seat, tab, interior slit or S-shaped rubber shorts. Trace a suspicious edge to its source before repair.
- **Garment semantics:** source length, full cuff circumference, cloth/skin boundary and both leg tubes survive every pose; no skin creep.
- **Contact/timing:** trace planted soles over time, not only ankle points. Avoid large support-foot jumps, floor penetration and unwanted flight. Longer frame holds do not interpolate a large spatial jump. Describe remaining staccato honestly.
- **Contours and loop:** ankles/socks remain inside shoe openings, no clipped toes/heels or changing shoe scale, coherent loop endpoints. Changing palette/color/shadow can flicker even with correct anatomy.

If correcting one reported defect, freeze the approved baseline, create a sibling revision, and compare changed pixel masks. Confirm unaffected frames and all pixels outside the intended region are identical where feasible. Keep cycle durations, phase order, foot registration and common upper transform unchanged unless the user requested changing them.

## Runnable CLI and portable project contract

Run from the matching engine root in a project-local Python environment (`requirements.txt`). Use `python drawn_cel.py --help` for the authoritative command contract. Start with `python drawn_cel.py template work/character/project.json`. This creates an intentionally incomplete JSON skeleton, not artwork or a renderable character. Fill it from real source PNGs and manual registration before validation/pinning. Do not point it at files outside that project directory.

The `drawn-cel-loop/1` project declares `representation` and two `legOwners`. In the standard `coherent-full-cel` path, each registration is `{source, scale: 1, translation: [0,0]}` and no upper cel is required; `character_workflow.py register-cels` writes this for aligned images. The following detailed source-waist fields apply only to advanced shared-upper/lower assembly:
- `canvas`, `frames`, `durationsMs` (positive multiples of 10 ms for exact GIF timing) and one `registration` per actual cel; each registration names its relative `source`, source waist landmark, `uniformLowerScale`, destination `translation` and `targetWaist`. Optional `clipRects` describe discarded source-owned regions explicitly. Legacy `clipOldRightHem` must be migrated to explicit `clipRects`; private-example offset assumptions are not supported in the generic route.
- For shared-upper/lower representation, a relative `upperCel` plus its authored anchor/translation. Choose its crop from that character, not a private example. Full-cel representation uses complete authored frames instead, without a forced upper cutout.
- Optional `connectionRestorePolygons` indexed by frame: source-space polygons that restore existing cloth behind the unchanged assembled cel. They do not synthesize missing anatomy.
- `identitySources`: preserved original reference paths, separate from generated cels. `sourcePins` bind relative source paths to SHA-256.
- Optional `coverageProbes` supply frame-indexed points and `minAlpha` for known interior seam locations. These detect transparent holes at those points only, not missing dark cloth, horizontal exterior cuts, wrong skin exposure or overall naturalness. Human `waist_connection` and `cloth_coverage` review is still mandatory.
- `phaseMetadata` per frame: `phase` (`contact`, `down`, `passing`, `up`, or `transition`), `supportOwner` and opposite `swingOwner` from the project’s two declared `legOwners` (for example `near`/`far` for side, anatomical left/right for front/back). Record these from visible anatomy, not merely from a desired script.

```sh
# After sources and manual registration are ready, pin the actual inputs.
python drawn_cel.py pin work/character/project.json
python drawn_cel.py validate work/character/project.json
python drawn_cel.py render work/character/project.json --out work/character/draft-01 --mode draft
# Inspect the exported images and actual loop BEFORE recording any gate.
python drawn_cel.py review work/character/project.json --gate identity --evidence work/character/evidence/original-comparison.png --note 'Describe the actual original/pose identity comparison performed'
```

Repeat `review` with genuine evidence and specific findings for all six gates:
`identity`, `phase_ownership`, `waist_connection`, `cloth_coverage`, `motion_contact`, `identity_stability`.

```sh
python drawn_cel.py render work/character/project.json --out work/character/reviewed-01 --mode reviewed-draft
```

Use new output directories. Reviews are stored separately in `PROJECT.reviews.json`, tied to the project/source/renderer-code fingerprint and evidence hashes. A matching, hash-pinned source already inside the project may be referenced in place; other evidence is copied under the project’s `review-evidence/` with content-hash names and relative references for portability; preserve those archived copies. Changing source, registration, renderer implementation or evidence requires fresh review; `pin` is not permission to bypass it. Never automatically fill review records after tests or use a dummy screenshot. An exact duplicated raster half-cycle or invalid declared owner exchange is a structural failure; a nonidentical but wrongly depicted repetition still requires human rejection.

The renderer exports `frame-NN.png`, `sheet.png`, `preview-native.gif`, `preview-128.gif`, `review-cyan.png`, `review-magenta.png`, `review-black.png` and `export.json`: only actual cels and their held timing. Do not assume the old editor GUI can open this separate JSON format or that adding 24 playback samples creates 24 new drawings. Before delivery, verify exported file names/metadata and the project round trip using the current tool output rather than assuming an earlier package's layout.

## Real-time acceptance, separate from assembly verification

Follow the mandatory normal-speed evidence gate in [quality review](../.agents/skills/sprite-motion-workflow/references/quality.md). Record reviewer/method, exact artifact hash, 1× playback, native/128 views, actual complete-loop counts and observed continuity. Extracted stills and duration metadata do not establish motion inspection. Without an actual video observation method mark temporal certification BLOCKED / UNREVIEWED. This does not stop safe authorized local fixes, static/alpha inspection or clearly labeled candidate delivery for user review; do not add approval gates for every intermediate. Identity/scale jitter is rejection, even if the poses individually improved. An immutable head/torso with separately authored free arms and coherent pelvis/legs is a possible alternative to unstable full cels, not an automatic fix; review all seams and motion before acceptance.

## 6. Reopen and hand off

Reopen the portable project and render it again; compare **all** output RGBA bytes, frame count, durations, scale/registration and source/evidence hashes. Save exact baseline identity for before/after comparisons: a separately retimed alternative is not the delivered version.

Private handoff: original sources, accepted generated cels and prompts, source/inferred ownership, saved project, actual RGBA frames/sheet, native/128 GIFs, QA evidence, review records and known limitations. Keep packages reasonably small (split source masters from runtime assets if needed). Generic source and skill bundles must contain only implementation, synthetic examples, templates and instructions. Neither one accepted character nor one direction establishes universal first-attempt success.

## Focused image-editing request templates

**Single pose / phase**
> Edit the attached original character reference into [PHASE] of a restrained [FACING] walk. [NEAR/FAR] leg is the planted support; the other leg [EXACT LOW RECOVERY ACTION]. Preserve original head/body ratio, face, [SOURCE HAIRSTYLE], [SOURCE CLOTHING/COLORS/LENGTH], [SOURCE ACCESSORIES], [HAND POSE], and [SOURCE SHOES]. If hands hold straps, keep that attachment. Do not add a ponytail, bag, charm or knee-length garment absent from the source. Draw pelvis→thigh→cuff as one coherent volume. Keep both leg identities and foreground overlap explicit. No high-knee march, back-kick, extra limb, shorter garment, or hidden face redesign. Transparent background. Mark inferred hidden surfaces in provenance after generation.

**Localized repair**
> Change only [SPECIFIC SOURCE REGION/DEFECT] in the attached cel. Preserve pose, foot placement, proportions, all other colors/shadows and upper-body identity. Restore [SOURCE-FAITHFUL CONNECTION/CUFF], not a new costume or wider shoe. Keep the existing curved outline and texture; no opaque cover patch. Transparent background. We will composite only the verified changed region.

## Independent arm surfaces and shoulder ownership

Read [the arm/shoulder reference](../.agents/skills/sprite-motion-workflow/references/arms-shoulders.md) before replacing hands or splitting upper layers. Palm/back-of-hand visibility is a source-specific observation; near/far arms need independent ownership. Preserve the sleeve cap’s relationship to the torso socket, inspect exterior matte and keep shoulder–elbow–wrist connected. An immutable head/torso with independently moving free arms and whole pelvis/leg cels can be viable, but is not a universal renderer preset or an automatically integrated shared-parts CLI. It requires authored/provider sources and manual independent-part/rig registration; the optional arm contract only records and conveys the intended source surfaces and joins. Preserve accepted motion during local repairs and verify the changed region without silently changing other anatomy or timing.
