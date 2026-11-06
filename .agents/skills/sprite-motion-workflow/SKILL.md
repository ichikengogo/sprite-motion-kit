---
name: sprite-motion-workflow
description: Create source-faithful sprite walk drafts with Sprite Motion Lab using coherent drawn cels or manually registered rigs; verify identity, near/far leg phase ownership, waist overlap, garment coverage and full-cycle motion. Use for repeatable production and localized corrections, not automatic anatomy or quality certification.
---
# Unknown character originals → source-faithful reviewed walk drafts

Use the companion **Sprite Motion Lab** engine (`workflow.py`, `server.py`, renderer modules and `requirements.txt`). The full repository includes that engine. A copied skill folder contains instructions only; obtain the companion project before claiming engine commands run. Project-local placement is `.agents/skills/sprite-motion-workflow/`. Keep private character artwork and registrations outside the generic skill/package. Follow the user's chosen installation and publication scope.

Read [runnable workflow](references/workflow.md) for intake, handoff, tuning and export. Read [visual gates](references/quality.md) before confirming parts, recording reviews, or delivering results.

## New character entrypoint (start here)

Use [the character workflow](references/character-workflow.md) and companion `character_workflow.py` for three unknown biped-character originals (not arbitrary multi-legged skeletons). Complete a source-specific profile (identity, proportions, clothing boundaries/length, accessories, free/held/absent arms, timing and per-view physical limb ownership) before provider-neutral drawing requests. Unset decisions stop planning. `plan` writes requests, not images: use the selected image tool, inspect actual generated artwork, use `register-cels --view VIEW --cells-dir DIR` for aligned coherent full cels without coordinate JSON editing, then bind/render all three. Shared-upper/lower remains an advanced manually registered path. No default child proportions, costume, backpack, capri length, held straps or private-character coordinates.

For side use declared near/far identity where appropriate; for front/back map anatomical left/right to screen sides deliberately. Choose full coherent cels when the whole body/arms need motion, or shared upper/lower only when authored contact and motion permit. These are per-view choices, not an automatic one-character template. Synthetic fixtures test workflow wiring without proving art quality on unseen characters.

## Choose the route before tuning

Read [drawn-cel production](references/drawn-cel.md) for coherent redraws, shared upper identity, alternate leg ownership and explicit source waist overlap. The companion `drawn_cel.py` provides a portable assembly/validation/review route. Prefer it when repeated mesh fixes deform the pelvis/garment or hide essential source surfaces; do not treat more opt-in deformation settings as a universal cure. Start with original-reference contact/down/passing/up, then a genuinely opposite half-cycle. Preserve source garment length and identity before adding inbetweens.

The existing `workflow.py`/editor route below remains for manually registered meshes and projected front/back. Choose per view and source; do not rebuild unaffected directions. The project formats and review commands are distinct. A drawn-cel project is not an editor rig and is not loaded through `workflow.py bind`.

For interval repairs, use the original plus both adjacent actual cels as simultaneous references. Verify support/recovery progression, retain constant identity/scale and the view-specific free/held arm condition. Review sole-marker distance divided by real frame time and face/hair/torso as a temporal sequence; extending holds is not creating inbetweens. See [transition generation and temporal art gates](references/character-workflow.md).

For both routes, human image/motion evidence is mandatory: opaque alpha, matching landmarks, no inversions and successful tests cannot certify cloth preservation or natural gait. An accepted private example is a regression target, not a transferable anatomy preset or guarantee of first-attempt success.

## Arms, hands and shoulder repairs

Use [the arm/shoulder workflow](references/arms-shoulders.md) for source-specific palm/back-of-hand visibility, independent physical-arm sources, sleeve-cap/socket ownership and exterior matte inspection. Preserve the connected shoulder–elbow–wrist chain, source cloth length/full circumference and true alternating physical legs. When viable, a shared immutable head/torso plus independently moving free arms preserves identity without freezing the source’s free-arm motion. This requires authored/provider assets and manual parts/rig ownership in the existing engine routes; the arm contract is not automatic segmentation or a complete shared-parts CLI. Local repairs retain accepted gait/timing and unrelated pixels. No universal palm orientation or per-intermediate approval gate is implied.

## Mandatory real-time art gate

Before claiming visual acceptance, actually observe the exact candidate at normal 1× speed, native and 128px, including repeated full loops and the loop join. Record reviewer identity, observation method/tool, artifact SHA-256, speed, actual loop count per size and specific continuity findings. Stills, extracted frames, durations and byte-exact tests are not playback observation. If no observation tool/reviewer is available, mark **temporal certification BLOCKED / UNREVIEWED**; never claim to have watched a GIF. Continue safe authorized local fixes and static/alpha/reproduction checks, and deliver clearly labeled candidates for user review when useful. Do not create an extra approval gate for every intermediate. Known identity/scale jitter is a rejection, not a tolerated “improved prototype.” See [mandatory temporal evidence](references/quality.md).

## Required production decisions for the existing three-view mesh/projected route

For an explicitly single-view drawn-cel task, use [drawn-cel workflow](references/drawn-cel.md) instead; do not require or generate unrequested directions.

1. **Identity before segmentation.** Inspect the three originals together: face where visible, hair silhouette, costume details/colors, accessories, shoes and orientation. A changed face or unexplained cross-view detail is a blocker, not something animation should hide. Ask for the correct original or explicit acceptance of an intentional variation. Rear views need not show a face. `init` validates files, not identity; record this judgment with `workflow.py identity` before registration. Its evidence is required for binding, but is a human assertion, not automated recognition.
2. Preserve each original and use its own view. Front/back are not a flipped side; opposite-facing side is not interchangeable when the design is asymmetric. Record screen-left/right versus anatomical left/right and near/far ownership. Never silently manufacture a missing view.
3. Manually register joints, masks, draw order and hidden regions per view. Geometric suggestions are not learned segmentation. Confirm source-pixel ownership and every required part; do not borrow a known character's rig or mark invisible anatomy confirmed. Generate missing raster artwork only within the authorized production scope; preserve inferred-region provenance and review it separately. Ask when a new design or direction would materially expand that scope, not for each routine intermediate.
4. Freeze a neutral proportion reference and **one constant scale per view**, with comparable neutral display height across views when requested. Keep real bob and pose foreshortening; never refit each frame's bounding box. Tune gait, opposed arms and surface deformation against the new character, not private calibration numbers.
5. Export all three as **draft** first, inspect every key and intermediate phase in normal color and high contrast, then record full gates and export a **reviewed-draft** if warranted. Both remain drafts, never automatically approved. Front/back are manually registered projected stepping, not reconstructed 3D walking.
6. Reopen saved JSON, reproduce exported RGBA frames, and check source/evidence freshness, frame count, timing and pivot. Distinguish completed work, unresolved defects and unsupported steps. Passing tests and numeric geometry do not certify appearance.

Example request: 「この正面・背面・横の3枚で同じキャラか確認してから、それぞれの原画で歩行を作って。全コマと中間姿勢を比較し、未解決部分はDRAFTのまま明記して」.

## Existing mesh route: optional side-walk hip initiation

If a side walk reads as calves dangling below a fixed waist, evaluate **motion before seam-only polishing**. The engine's optional `walkHipDrive` (side/simple/source hip registration only) adds calibrated pelvis transfer, restrained torso counter-motion and whole swing-leg rotation about the actual hip without changing bone lengths. See `docs/REUSABLE_WORKFLOW.md` in the companion engine for field ranges. Optional `gaitCenter: "source-ankles"` retains each source ankle's projected stride center instead of forcing both onto a shared center; use only after checking source perspective and paired half-cycle support. Defaults, dash and neutral artwork remain unchanged. Review timed native/128px playback and all 8 keys +24 intermediate phases; check thigh initiation, stance stability, the source-specific arm/hand contacts, cloth roots and ankle continuity. Never replace character-specific calibration with private example coordinates or treat tests as motion approval.

## Explicit layered motion and production diagnostics

Read [layered production](references/layered-production.md) when preserving a fixed head/torso with independent authored limbs or checking newer ownership/support-exchange failures. `layered_motion.py` uses explicit full-canvas layers and poses, bounded shoulder-root blending and optional support-only height fitting; it does not discover parts or solve grounding automatically. `production_audit.py` checks neutral alpha coverage, measured landmark timing, repeated endpoint frames and temporal record freshness. A clean diagnostic is not correct ownership, plausible anatomy or observed playback. Use the actual original, complete silhouette, all phases and normal-speed observation to decide.

## Authored dash corrections

Read [dash repairs](references/dash-repairs.md) for shared-head/body-axis stabilization, arm shaft length versus fist scale, shoulder-root-preserving widths, source-pinned per-view projects and clean reproduction. Use these optional corrections only when the actual new source and intended gait call for them. A matched axis, fixed head or passing checksum does not establish attractive motion; do not transfer another character's measurements or temporal acceptance.
