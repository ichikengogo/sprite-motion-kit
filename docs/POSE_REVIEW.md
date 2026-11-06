# Pose-specific hand and posture review

This workflow makes review scope reproducible. It binds observations to actual authored frames, physical arm identities, view, phase and source hashes. It does **not** recognize anatomy, infer a palm, decide which way a thumb faces, or establish natural motion. An accepted user result and an independently observed playback review remain separate facts.

## Run the reproducible worksheet example

```sh
python pose_review.py --root output/pose-demo demo
python pose_review.py --root output/pose-demo check manifest.json review.json --out check.json
```

The explicit demo command creates original geometric PNGs, an input manifest and an entirely `UNREVIEWED` worksheet. It is a technical fixture, not a correctly drawn hand or complete gait. Importing/checking the module does not generate or change artwork. Existing output files are never overwritten.

For your own requested view, author a manifest and keep it with the actual sources and cels in a private project directory:

```sh
python pose_review.py --root work/character init manifest.json review.json
python pose_review.py --root work/character check manifest.json review.json
python pose_review.py --root work/character check manifest.json review.json --require-recorded --out check-recorded.json
```

The first `check` validates structure, coverage and freshness even if observations remain unreviewed. `--require-recorded` additionally requires an authored inspection record for every declared frame/arm row. `RECORDED` means an assertion exists, **not** that the image meets the intent. Neither mode performs visual recognition or playback. All paths, including output and symlink targets, must remain within the project root.

The report's `checkScope` states that limited scope. Read `authoredAssertionDifferences` and `unresolvedAssertions` as well as `checkPassed`: an expected palm and an observed back-of-hand remain an explicit disagreement even when every record is structurally complete. Unknown/occluded assertions are listed, not promoted to acceptance. This comparison checks authored labels, not pixels or the truth of either assertion.

### Input manifest and worksheet

Use schema `pose-review-input/1`, with `view`, `facing`, `canvas: [width,height]`, one declared `fixedScale`, `sources: [{id,path}]`, `physicalArms: [{physicalArmId,anatomicalSide}]`, and an ordered `frames` list. Each frame supplies a unique `id`, PNG `path`, positive `durationMs`, explicit `phase`, and an `armMapping` object with `nearFar`/`screenSide` for every physical arm. The generated example contains the complete shape. The actual frame order is this list, not a filename sort. A requested single view is sufficient; no unrelated direction must be invented.

All actual cels share the declared canvas. Original reference PNGs can retain their own native dimensions; those dimensions and their exact bytes are recorded without resizing. `fixedScale` is your declaration, not an automatic scale measurement. Actual authored cel count and positive hold durations are recorded separately from encoded animation frames.

Each authored cel has one row per declared physical arm. Fill `expected` separately from `observed`; neither copies into the other. Mark `reviewStatus: "RECORDED"` only with a reviewer and concrete findings. Unknown/occluded features remain honest unknowns; a partially visible hand can have some observed and some occluded fields. The tool cannot discover an arm or a source image omitted from the manifest, so inspect coverage against the actual artwork.

The worksheet binds the exact source/cel bytes and manifest context, including view, mapping, timing and order. Changed inputs make old assertions stale. Reinitialize in a new worksheet and reinspect; do not copy old findings merely to silence the failure. Hashes are evidence links, not authenticated proof of who reviewed or what they saw.

Optional `landmarks[frameId]` records have a `reviewer`, and may include `pelvis: [x,y]`, `arms` keyed by declared physical arm ID, and `legs` keyed by explicit physical leg ID. An arm uses `shoulder`, `elbow`, `wrist` points and optionally `handMaskPixels` as unique integer `[x,y]` indices. A leg uses `hip`, `knee`, `ankle` and a declared `phase: support/recovery/unknown`. Pixel coordinates have x right and y down; a pixel's center is its index plus one half. Missing measurements remain null/unmeasured. No pose or support is inferred.

## Why the checks are independent

A replacement can have the correct area and a connected silhouette while showing the wrong hand surface. It can show a palm while putting the thumb on the wrong side in the posed frame. It can place the thumb correctly while making a raised fist read as a forward punch. Passing any one of those checks is not passing the others.

For every actual cel and every relevant physical arm, record:

- **Surface:** palm, dorsal/back, edge, mixed or hidden, with the visible evidence and uncertainty.
- **Thumb-side facing:** the side/volume/pressing surface relative to the body in this view. Do not replace this with a literal fingertip vector.
- **Fist attitude:** the fist mass relative to the wrist and forearm in a named pose. Upright in a key pose is not a requirement to remain world-up throughout the cycle.
- **Attachment and fingers:** coherent forearm, wrist, palm, thumb root, curled fingers and cuff. A connected alpha mask cannot identify digits or establish anatomy.
- **Mapping:** physical/anatomical identity versus screen side and near/far depth. An occluded region remains unobserved, not automatically correct.

Inspect the actual composited reference pose at native size and enlargement before spreading a changed hand through the cycle. Then inspect all phases, including both swing extremes and partial occlusions. Do not judge a registered hand only from a neutral atlas. Fine fingers may be unreadable at the intended small display size; use the native detail as well, without pretending the small preview proves that detail.

These are internal production checks under the existing task scope, not a new permission request for each intermediate.

## Carry intended hand details into drawing requests

The existing `character_workflow.py` arm contract accepts an optional `handPoseIntent` object on each `armSurfaceSpec.arms` record:

```json
{
  "thumbSide": "Describe the intended thumb-side surface relative to this body/view.",
  "fistDirection": "Describe the fist relative to the wrist and forearm in the reference pose.",
  "wristAndFingers": "Describe the continuous wrist/cuff transition and intended grip.",
  "phaseContext": "Describe how the relationship changes through swing and occlusion."
}
```

Replace these descriptions from the actual character and request; they are not a ready-made anatomy preset. Missing/null means unrecorded. All four fields must be nonempty text when the object is supplied. The existing `visibleHandSurface` remains a separate requirement. `plan` and `transition` preserve the complete intent, while `automaticSemanticValidation` stays false. Editing intent invalidates the previous intake fingerprint.

## Dimensions without anatomy claims

Use explicitly authored masks, not a universal skin-color threshold. Compare at one source scale: width/height, mask area and centroid relative to a declared wrist can reveal a shrunken replacement or altered silhouette. A new aspect ratio can be intentional. Mask area is not anatomical volume; a rotated bounding box is not hand scale; centroid direction is not thumb direction.

Keep one crop size and one zoom for tracked comparisons. Move the crop with an explicitly authored anchor and pad canvas overflow. Never fit each crop to its own content, which conceals size changes.

The Python API `tracked_region_sheet(images, anchors, crop_size, zoom, columns=4)` accepts an ordered list of PIL images, one integer `[x,y]` anchor per image, a single `[width,height]` crop size and a positive integer nearest-neighbor zoom. It returns an RGBA sheet with transparent padding outside the shared canvas. For before/after comparisons, use the same crop size and zoom and deliberately corresponding anchors. It neither tracks a wrist automatically nor edits the source images. The selected region may omit a defect, so inspect full-body images too.

If the intended correction needs a different palm surface or wrist anatomy, author the missing surface rather than declaring a mirror/rotation anatomically correct. Retain inferred-surface provenance. For a hand-only change, keep the established shoulder–elbow–wrist path and adopt only the required hand/wrist/cuff region, rather than unintentionally replacing a whole sleeve.

## Waist height and support knees

Exact bone lengths do not guarantee an appropriate running posture. A character may still look crouched because of pelvis height, contact placement and a tightly folded support knee. Compare the source's posture and proportions with explicitly measured hip, knee, ankle and contact landmarks in the **declared** support phase. Review shoe orientation and the full silhouette too.

Knee angles and hip-to-ankle reach are two-dimensional projections, not recovered joint anatomy. There is no universal correct knee angle, waist rise, hand-area ratio or bob profile. Do not fix perceived stature by silently stretching the torso/limbs or normalizing every frame's bounds. A repeated landing displacement can be an intentional phase choice rather than an endpoint duplication; evaluate its speed/impact in actual playback before calling it smooth or defective.

## Preserve ownership and local scope

Give each visible strap, sleeve cap, hand and shoe a deliberate source owner. Intentional hidden socket overlap is often necessary. Zero overlap is not a goal, and coverage cannot prove semantic ownership. Inspect shoulder joins and exterior matte in the actual composite, not only in isolated parts.

Freeze the actual previous export, define a meaningful allowed local mask, and use `repair_audit.py` to compare outside-mask RGBA and timing. An all-white mask proves no localization. Verify that the final exported frames are exactly the frames that were reviewed. A harmless pre-existing shadow should not be reclassified as fixed, and a negative finding is not evidence that the latest repair changed that area.

## Keep evidence classes separate

1. Source/freshness and coverage checks establish which files and declared rows were checked.
2. Geometric measurements describe authored coordinates and masks.
3. Static visual observations record what a reviewer could see in exact frames.
4. Temporal observations require actually watching the exact candidate at normal speed and intended sizes, with real loop counts and findings.
5. User acceptance records the user's decision; it does not retroactively prove an independent playback observation.

Hashes, GIF decoding, frame counts, contact sheets and clean regeneration do not establish item 4. Keep `visualApproval: false` and temporal status `UNREVIEWED` in automatic diagnostic output. A human record is still an assertion, not an automatic certification of its truth.
