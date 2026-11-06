# Sprite Motion Lab

A local, provider-neutral toolkit for building and reviewing **front, side and back 2D character animation** from your own artwork.

**Experimental, human-reviewed tooling.** This is not a model that turns three pictures into finished animation. You supply or author the visible and hidden artwork, register physical limb ownership and joints, and review the actual result. Tests and metrics do not certify natural motion.

[日本語](README.ja.md) · [Workflow](docs/CHARACTER_WORKFLOW.md) · [Production checks](docs/PRODUCTION_CHECKS.md) · [Agent skill](.agents/skills/sprite-motion-workflow/SKILL.md)

## Start locally

Python 3.10 or newer. Node.js 18 or newer is needed only for the browser-unit tests, not to use the editor.

```sh
python -m venv .venv
# macOS/Linux
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

Open http://127.0.0.1:8765 on the **same computer**. The editor has original geometric demos for all three views, image import, manual polygon masks, joints, per-part replacement, playback, scrubbing, and PNG-sheet/JSON export. It binds only to loopback. Do not expose this development server to the internet.

Generate a playable geometric walk without the editor:

```sh
python cli.py --view side --action walk --output output/demo
python synthetic_profiles.py --out output/fixtures --workflow-out output/workspaces
```

The second command exercises two original shape-based characters with different proportions, clothes, held/free contacts, frame counts and all three views. Use fresh output directories. These diagrams demonstrate reproducibility and workflow wiring, **not production art quality**. All images are generated locally from code; no private art is distributed.

## Choose a route

- **Unknown character intake:** `character_workflow.py` preserves three source PNGs and requires explicit identity, clothing, contact, ownership and timing decisions before writing provider-neutral art requests. It does not call an image model. Register real authored cels, bind and render. [Guide](docs/CHARACTER_WORKFLOW.md)
- **Authored cels:** `drawn_cel.py` assembles coherent full-body cels or shared-upper/lower cels with explicit registrations and source hashes. [Guide](docs/DRAWN_CEL_WORKFLOW.md)
- **Manually registered parts:** `motion.py`, `projected_walk.py` and the local editor provide rigid/IK and optional mesh paths. Front/back are 2D projections, not recovered 3D geometry. [Guide](docs/REUSABLE_WORKFLOW.md)
- **Explicit layered motion:** `layered_motion.py` is the newer authored-layer route with bounded socket attachment, a common physical phase convention and support-only height fitting. It needs complete authored layers and joint tracks; it does not automatically split or rig artwork. [Guide](docs/LAYERED_MOTION.md)
- **Diagnostics:** `production_audit.py` reports source-alpha omissions/overlap, actual timed landmark motion, adjacent repeated frames and stale temporal review records. `repair_audit.py` checks exact pixels outside an explicit edit mask and optional GIF timing. Neither tool awards visual approval.

Examples and usage for each command are available with `--help`.

## Reproduce authored dash repairs

`dash_registration.py` provides explicit body-axis registration, integer-only shared-head placement, shaft-length changes that preserve the hand, and shoulder-root-preserving width adjustment. `dash_project.py` pins source PNGs and reproduces a saved per-view project into real RGBA frames, GIFs and honest diagnostic reports. See [dash reproduction](docs/DASH_REPRODUCTION.md).

```sh
python dash_project.py demo output/dash-example
python dash_project.py verify output/dash-example/project.json output/dash-example/rendered
```

The example uses original geometric shapes. Real artwork still needs authored landmarks and actual playback review; a faster walk is not automatically a dash.

## Preserve the hard-won invariants

1. Keep originals immutable and one constant scale per view. Never resize every frame to its own bounding box or redraw the face to conceal registration errors.
2. Give each physical arm, hand, leg and shoe a stable owner. Check the entire ink/antialias boundary. Skin-color segmentation and row cutoffs can leave floating outlines or clipped clothing.
3. Neutral coverage and moving attachment are separate checks. Intentional hidden cloth/socket overlap is often required; a perfect non-overlapping cut can open a slit once moved.
4. Inspect near and far shoulder roots separately, the whole shoulder–elbow–wrist chain, sleeve volume, cuff circumference and the actual hand surface. Thumb position alone does not establish a palm.
5. Derive front/back visible depth, foreshortening and occlusion from a coherent physical cycle. A variable named “opposition” does not prove readable opposed limbs.
6. Check every exported frame and dense intermediate phases, especially support exchange and last→first. Four plausible key poses can hide a body drop, knee snap or direction reversal. Sample a cycle on `[0,1)`, without automatically repeating the endpoint.
7. Review the exact output at normal speed, native and intended small size. If continuous playback was not observed, say **UNREVIEWED**. A contact sheet, equal hashes and timing metadata are not a watched animation.

See [production checks](docs/PRODUCTION_CHECKS.md) for detailed lessons and the evidence template. User acceptance, structural checks and independent visual review are separate records. Outputs stay drafts unless a human makes a scoped quality decision.

## Run checks

```sh
python -m unittest discover -s tests -v
node tests/test_coordinates.cjs
node tests/test_playback.cjs
node tests/test_project_load.cjs
node tests/test_render_status.cjs
node --check web/app.js
python scripts/check_public_release.py
```

[QA scope](docs/QA.md) distinguishes numerical/structural tests from playback observation. [Contributing](CONTRIBUTING.md) describes clean fixture and release rules.

## Install the agent skill

This repository includes `.agents/skills/sprite-motion-workflow/`. Compatible agents can discover it in the checkout. For a personal installation, copy that folder to your agent's skills directory, for example `$CODEX_HOME/skills/` or `~/.codex/skills/`. The skill contains portable instructions and references; rendering requires this companion Python checkout. Do not copy your artwork/workspaces into the skill.

## Privacy, provenance and license

There are no external API calls, telemetry, remote fonts, embedded model weights or credentials in the runtime. Dependency installation normally requires network access. Local browser imports are sent only to the local server during generation, not to an external provider. The editor's saved JSON may contain original image data: keep it private unless you intend to share it.

Source, documentation, and code-generated geometric fixtures are licensed under [MIT](LICENSE). Your imported/generated artwork is **not automatically licensed by this project**. Check its rights and provider terms separately. Dependencies retain their own licenses; see [DEPENDENCIES.md](DEPENDENCIES.md) and [PROVENANCE.md](PROVENANCE.md).
