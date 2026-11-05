# New character workflow: three originals → reviewed animation assets

Start here for a new **biped character with front/side/back originals**, not at a calibrated example project. This contract does not support every possible multi-legged or non-biped skeleton. `character_workflow.py` is the common intake/planning/binding/export entrypoint. It preserves three originals, requires character-specific visual decisions, emits provider-neutral drawing requests and connects authored per-view projects to the renderer. It does **not** recognize anatomy, call a model or automatically produce high-quality artwork.

## 1. Preserve the three actual originals

From the engine root, with its local environment and `requirements.txt` installed:

```sh
python character_workflow.py init --front /path/front.png --side /path/side.png --back /path/back.png --out work/new-character
```

Use a new directory. Read the returned profile path (`work/new-character/character-profile.json`). `init` also writes `character-workspace.json` and preserves `inputs/{front,side,back}.png`. Originals are private project inputs, not generic example assets. Do not substitute a flipped side image for another view or copy another character's body dimensions. Confirm ownership/license of supplied artwork independently of the software's MIT license.

## 2. Inspect and complete the character profile

Open all three originals together at native detail and comparable reference scale. Read alpha on contrasting backgrounds. Resolve mismatched identity or unexplained costume differences before segmentation/generation. Fill the generated profile's initially unset fields; unset decisions intentionally block planning.

| Profile field | Required human decision |
|---|---|
| `identity.descriptors` | Specific visible face/head silhouette, hair, colors, markings and cross-view identity anchors; no default ponytail, age, costume or accessory. |
| `proportions.notes` | Actual head-to-body ratio and torso/limb/foot proportions, source scale and any intentional cross-view stylization. Do not impose a prior character's measurements. |
| `clothing` | Each `{name, boundary, length}`: where the garment meets body/other garments, complete hem/cuff silhouette, and source length. Shorts, long trousers, dresses, armor and exposed limbs differ. Use explicit `[]` if none. |
| `accessories` | Each `{name, behavior}` with `rigid` or `flexible`; where attached, what can move and what cannot. Use `[]` if absent. Never assume a backpack/charm. |
| `contacts` | `armMode`: `free`, `held` or `none`, plus a nonempty `held` contact list for held mode, or `held: []` otherwise. Free arms need appropriate phase opposition; held hands must maintain their source attachment. Do not lock free arms merely because a previous character held straps. |
| `timing` | An even number of positive `durationsMs` (multiples of 10 ms) and matching `phases` (`contact/down/passing/up/transition`) for the full cycle. Exactly two contact keys start the first and second halves; owner A supports in the first half and owner B in the second. Choose cadence and actual frame count, not a universal eight- or ten-frame default. |
| `views[VIEW]` | Optional `armSurfaceSpec` records separate physical-arm hand surfaces, pose, contacts and shoulder/elbow/wrist continuity; null/omission remains unknown. See the arm reference for exact fields and source-specific choices. Optional `contacts` overrides the global arm/contact decision for this view (`null` inherits); optional `occlusionNotes` records observed hidden regions and inferred surfaces. Actual `facing`; `representation`: `coherent-full-cel` or `shared-upper-lower`; `ownership`: `ownerA`, `ownerB`, `basis`. Choose by the source and required motion, separately per view. |

### View rules

- **Side:** usually `near-far` ownership; record which original limb is near and keep its identity as it advances or trails. State facing direction. Opposite half-cycle must exchange support and recovery, not repeat the same silhouette.
- **Front/back:** use `anatomical-left-right` ownership and explicitly map those labels to screen sides in each view. Back-view screen-left is not automatically the same physical leg as front-view screen-left. Keep the source perspective; do not blindly reuse side contact silhouettes or near/far conventions. Generate or author that view's real artwork.
- **Coherent full cels:** best when arms, torso, loose clothing or perspective need coordinated whole-body changes. Each cel is an authored pose, with identity matching reviewed across frames.
- **Shared upper/lower:** only when the source pose and requested motion permit an unchanged upper cel. This can stabilize face/accessory/held-hand identity, but is not a universal default. Register the complete lower-body cel and source-owned overlap behind the hem; do not sever the rear waist with a horizontal cut.

## 3. Record actual intake review, then emit drawing requests

Save a real original-comparison image and complete profile. Then:

```sh
python character_workflow.py review-intake work/new-character/character-profile.json --evidence work/new-character/evidence/intake.png --note 'Specific identity, proportions, garment boundaries, accessory and arm-contact decisions actually checked across all three originals'
python character_workflow.py plan work/new-character/character-profile.json
```

Use the actual profile path emitted by `init` if different. Intake evidence is a human assertion, not automatic recognition. Changing original/profile content requires renewed review. `plan` writes source-bound, per-view/per-phase requests to `generation-requests.json`; inspect those requests. It does not silently generate art, contact a provider, spend credits or require an API key.

## 4. Fulfill requests using the chosen image tool or artwork workflow

The **provider boundary is explicit**: feed the original reference and planned request into an authorized image-generation/editing tool of your choice, or use legitimately authored artwork. Preserve the prompt/request, source hash, resulting image and inferred-region notes. Do not silently substitute procedural filler for the requested authored surface. Technical crop/mask/registration/composition is separate from drawing new surfaces.

Start with readable contact/down/passing/up directions, then complete both physical leg roles and targeted inbetweens. If direction needs user approval, ask in the context of that task; do not add approval gates beyond what is needed or already authorized. Review pose geometry and identity before spending effort on final exports.

Character-neutral request pattern:

> Use the attached **[VIEW] original** as identity and proportion reference. Create **[PHASE]** for **[FACING]** walk at the planned scale/ground. **[OWNER A/B]** supports while the other **[RECOVERY ACTION]**; preserve the declared foreground/occlusion order. Retain **[PROFILE IDENTITY DESCRIPTORS]**, **[GARMENT BOUNDARIES/LENGTH]**, **[ACCESSORIES AND ATTACHMENTS]**, and **[FREE/HELD/ABSENT ARM CONDITION]**. Keep pelvis→leg→garment volume coherent. Infer only the hidden surfaces required for this pose and record them. Do not introduce another character's costume, body ratio or accessories. Transparent background if required by the selected representation.

Generate the opposite half-cycle with reversed **physical support owner**, not by changing a label after generation. For front/back, judge depth/foot-lift from their original perspective. If a tool returns an unchanged role or wrong garment, reject that candidate; hashes and declared metadata do not prove depicted anatomy.

### Repair transitions using both adjacent actual cels

A correct single-pose description is not enough. A generated “up” can still depict down/support compression, or a recovery foot can return backward between two individually plausible drawings. Before exporting a full cycle, place the preceding and following **actual cels** beside the original reference and inspect their roles and silhouettes together. If a transition fails, retain acceptable cels and generate only that interval; do not regenerate every view or lock free arms to imitate another character.

A transition request must include:
1. The immutable original for identity, proportions, actual costume and per-view arm/contact condition.
2. The exact preceding and following cels, their physical support/recovery owners, positions in the cycle and durations. Include last→first explicitly when repairing the loop boundary.
3. The desired intermediate fraction/phase, a continuous planted-foot path and recovery-foot travel **toward the next cel**, with the intended occlusion order.
4. One fixed canvas, ground/reference scale and consistent head/body dimensions. No per-cel bbox stretching, shoe scaling or silent character redesign.
5. The constraints to preserve: free arm opposition stays free; held contacts stay attached; no new costume/accessory, shifted garment hem or independent face/torso style.

Provider prompt pattern:

> Image 1 is the original identity reference. Images 2 and 3 are the preceding and following actual cels in that order. Draw only the missing transition between them at [FRACTION/PHASE]. Preserve original identity and constant reference scale; do not average or crossfade the two raster images. Keep [SUPPORT OWNER] planted along the expected continuous support path, while [RECOVERY OWNER] advances from Image 2 toward Image 3. Preserve [VIEW CONTACT/ARM CONDITION], garment boundaries, shoe proportions and foreground ownership. Produce one coherent pose, not a duplicate endpoint or a new unrelated stance. Keep canvas and ground fixed.

Generate a source-pinned handoff for a specific interval:

```sh
python character_workflow.py transition work/new-character/character-profile.json --view side --from-index 1 --to-index 2 --from-cel work/new-character/side-cels/cel-01.png --to-cel work/new-character/side-cels/cel-02.png --fractions 0.5
# Two requested positions can instead use --fractions 0.333 0.667.
# To inspect the loop boundary, supply the actual last index and --to-index 0.
```

Indices are examples: choose the actual failed interval. The command archives both PNGs by hash in `transition-inputs/` and writes `transition-VIEW-FROM-TO.json` (or a new `--out` path). It includes the immutable original, both actual images, profile invariants, physical owners and elapsed cycle time. Fractions must be increasing, unique and strictly between 0 and 1; they are requested temporal positions, not inferred biomechanics. Endpoints must have the same canvas. Forward intervals crossing the end of the cycle are supported. Existing requests are preserved rather than overwritten. The profile, timing, registered projects, bindings and accepted exports are **not modified**.

A request file does not create the image or automatically insert it. Inspect the produced cel with **both** neighbors, then re-register/review a new candidate with the explicitly chosen timing. If inserting one or two cels, preserve existing keys and intended cycle timing where feasible; explain any deliberate change. Longer holds or a slower GIF are not new inbetween drawings and cannot remove a spatial jump.

### Arms and shoulder source decisions

For each physical arm, inspect source-specific palm/dorsal/edge visibility and thumb side; never force a universal palm view. Keep independent near/far sources and explicit sleeve-cap/socket ownership, preserve shoulder–elbow–wrist continuity and original sleeve/cuff coverage, and inspect exterior matte on contrasting backgrounds. When viable, use an immutable head/torso with independently moving free arms and coherent pelvis/legs rather than full-body identity drift or a forced fixed upper body. This is a provider/manual-parts registration decision using the existing mesh/projected or drawn-cel routes, not a newly integrated automatic shared-parts renderer. See the [arm/shoulder worksheet and local repair procedure](arms-shoulders.md).

## 5. Register and bind each view's actual assets

### Standard full-cel path: no coordinate JSON editing

Ask the drawing provider to deliver every accepted pose at the same canvas, reference scale and ground, in the intended phase order. Inspect that they really are aligned—registration does not repair inconsistent artwork or crop each bounding box to fit. Place that view's PNG cels in a private input directory with deterministic numbered names.

```sh
python character_workflow.py register-cels work/new-character/character-profile.json --view front --cells-dir work/new-character/front-cels
# Repeat for side and back using their own actual PNGs.
```

`register-cels` checks the profile's required cel count and common canvas, then copies the original and cels under `projects/VIEW/sources/`, creates `projects/VIEW/project.json` with scale 1 and translation 0, pins its inputs and binds it to the view. It does not require source waist/hip coordinates for coherent full-frame cels and does not silently warp artwork. The command binds automatically; after registering all three views:

```sh
python character_workflow.py render work/new-character/character-profile.json --out work/new-character/draft-01 --mode draft
```

### Advanced shared-upper/lower path

Only when appropriate for this character, create a manually calibrated per-view `drawn-cel-loop/1` project **inside the workspace**, with representation and each physical owner's identity explicit. Its identity references must include that view's preserved original hash. `drawn_cel.py template` is a registration skeleton, not artwork. Retain source masks and source-owned waist overlap. See [drawn-cel assembly and review](drawn-cel.md) for exact fields, source pins and human gates. `drawn_cel.py pin PROJECT` and `validate PROJECT` precede `character_workflow.py bind ...` for these authored projects.

All three views must be bound with fresh intake and matching source provenance. Binding an external example is not a shortcut. Generated images are required between `plan` and `register-cels`/`bind`; this is a human/tool production step, not yet an automatic model adapter. Standard full cels register automatically without per-frame coordinate editing; advanced shared-upper registrations are still manual. Existing mesh/editor workflows remain available separately; do not claim this entrypoint automatically converts arbitrary rigs or reconstructs 3D.

## 6. Review actual outputs, then export reviewed drafts

Inspect every real cel at native and 128px, normal color and high contrast, plus timed loops/endpoints for all three views. Trace both physical feet through the full cycle. Check identity and proportions, free-arm opposition or held contacts, accessory rigidity, shared/full pelvis, garment length and outer circumference, waist attachment, ankle/sole continuity and contact timing. A single alpha probe cannot detect skin replacing cloth; repeated holds are not drawn inbetweens.

### Temporal art gate: inspect more than the contact sheet

Use an annotated time strip and real playback at native/128 size. For each foot, mark a consistent sole/heel point (not just ankle) on consecutive actual cels and record displacement divided by the actual time interval, `distance / Δt`. Review large changes in this estimate against support/recovery state; there is no universal pixel-speed threshold. In-place stance normally travels backward relative to the canvas, so distinguish that intended travel from a jump or unintended slide. A longer hold can alter speed estimates without creating any missing pose.

At the same time, inspect the **face → hair silhouette → shoulders/torso** sequence against the immutable original. Track reference landmarks at fixed scale and note changing eye/cheek shape, head width, hairstyle volume, torso thickness or leg-to-body ratio. Account for real bob and pose foreshortening; do not normalize each frame to hide inconsistencies. Small identity/proportion changes across independently generated cels can flicker even when no alpha holes exist. Compare all views, but do not impose identical poses or invent a face in the rear view.

Optional descriptive marker report:

```sh
python character_workflow.py landmark-report work/new-character/character-profile.json --view side --annotations work/new-character/evidence/side-landmarks.json
```

The annotation JSON uses `schema: "character-landmarks/1"`, the selected `view`, an explicit `coordinateSpace` description, and a `frames` list. Each observed row has `celIndex`, optional `feet` mapping the project's physical owner names to `[x,y]` sole markers, optional `pelvis: [x,y]`, and optional `faceBox: [left,top,right,bottom]`. Use coordinates you actually measured on a common registered canvas; omit unknown observations rather than guessing them. The command writes `landmark-report-VIEW.json` (or a new `--out`) with per-interval distance/time, pelvis and face-box changes, including the loop boundary. It does not detect landmarks, classify identity or declare a pass. Missing observations remain `unknown`; face boxes cannot establish eye/cheek or hairstyle consistency, so the image sequence still needs review.

The `motion_contact` and `identity_stability` human gates need this temporal evidence and candid notes, including unresolved staccato or identity differences. Numeric registration, hashes, phase labels, a few markers, and “all tests pass” are not an art-quality verdict. A correct repeated cycle can remain unattractive or unnatural. Known identity/scale jitter or discontinuous motion rejects art acceptance; labeling it a prototype does not make it an acceptable improvement.

Record genuine per-view `drawn_cel.py review` evidence for all required gates (see that guide), then:

```sh
python character_workflow.py render work/new-character/character-profile.json --out work/new-character/reviewed-01 --mode reviewed-draft
```

Reload the profile and bound projects, rerender and compare every RGBA frame, timing and source/evidence hashes. Keep baseline/private sources separate from generic source/skill releases. Report unresolved limitations and whether image-provider steps, visual review, round-trip reproduction and regression tests actually ran.


## Mandatory real-time temporal review — an art acceptance gate

A normal-speed motion review is required before independently certifying temporal quality. Clearly labeled candidate delivery for user review and user acceptance are separate from this certification. A contact sheet, extracted GIF frames, GIF duration metadata, matching RGBA bytes or passing tests **is not real-time playback inspection**. Do not say “watched the GIF” when only stills or timestamps were available. “Improved prototype” or “presentation possible” is not a substitute for acceptance of the actual motion.

Record all of the following in temporal review evidence:
- Reviewer identity (human or named agent) and the actual observation method/tool.
- Exact reviewed GIF/video artifact path and SHA-256; distinguish alternatives and retimed versions.
- Playback speed (normal 1× required), native-size and 128px viewing, and the actual number of complete loops observed at each size.
- Observations across consecutive frames and the last→first join: physical support/recovery continuity, contact/foot travel, pelvis/torso connection, face/head/hair/torso scale stability, clothing/accessory continuity, and source-specific free-arm or held-contact behavior.
- Explicit outcome: accepted for the stated scope, rejected with defects, or **BLOCKED / UNREVIEWED**. A bare checkbox or copied “looks natural” note is insufficient.

The current CLI stores hash-bound human assertions; it does not watch video or verify that playback observations occurred. Include a project-local temporal report (`reviewer`, `methodTool`, `artifactPath`, `artifactSha256`, `speed`, complete-loop counts for both sizes, `continuityFindings`, `outcome`, `unresolvedDefects`) as review evidence. Use unknown/null values where observation did not happen. A `reviewed-draft` label cannot override a blocked or rejected art gate.

If no available tool or reviewer can actually observe normal-speed video/animation, mark this gate **BLOCKED / UNREVIEWED**, state that only still-frame/structural checks were completed, and request appropriate real-time review. Do not infer smoothness from extracted frames or fabricate a playback method, loop count or observation. Missing playback observation does not block safe authorized fixes, static/alpha inspection or reproducibility checks. Clearly labeled candidates can be delivered for user review within the task; report temporal certification as BLOCKED / UNREVIEWED rather than claiming observed smoothness. Do not invent a universal approval gate for each intermediate.

Known identity, head/torso scale or silhouette jitter is a **rejection**, not a tolerated shipping limitation merely because another defect improved. Likewise reject unresolved support-foot jumps, reversing recovery, or visibly discontinuous body/cloth motion. Keep the previous accepted baseline; preserve the failed candidate as evidence, not as a new quality baseline.

When independent full-cel drawings cannot retain identity/scale, consider a different representation before more generation: an immutable source head/torso, independently authored free-arm layers (when the source calls for arm swing), and coherent whole-pelvis/leg authored layers. Held contacts need their own source-faithful attachment handling. This is a design alternative requiring ownership, occlusion, seam and real-time review—not an implemented automatic fix or a guarantee of natural motion. Do not freeze free arms merely to stabilize the face, and do not split pelvis/garment back into the rejected deforming pieces.

## What tests establish—and what they do not

Synthetic three-view fixtures without an API key can prove intake blocking, profile customization, phase plans, source binding, output wiring, review freshness and deterministic pixels. They **do not prove** that an unseen character will be drawn attractively or that a model will obey every prompt. A private approved animation proves that specific rendering recipe can be reproduced; it is not sufficient evidence of new-character generation quality. First-pass reliability improves by capturing required decisions and rejecting the known failure classes, not by claiming universal success.

This is a local workflow with a public-ready separation of code, docs and private inputs. The toolkit is MIT-licensed; imported artwork retains its separate rights. A global skill install or remote deployment is not implied.
