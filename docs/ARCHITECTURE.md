# Architecture

The toolkit has separate explicit-input routes. Project formats are not interchangeable.

- `demo.py`: original geometric separated layers.
- `motion.py`: 384px rig validation, pure poses, rigid cutouts, fixed-length IK and optional surface mappings.
- `joint_mesh.py`, `garment.py`, `hip_cloth.py`, `projected_walk.py`: opt-in 2D deformation/projection helpers; no 3D reconstruction or physical cloth solver.
- `server.py` and `web/`: loopback JSON API and standard Canvas/fetch editor; no package manager or remote runtime dependency.
- `drawn_cel.py`: hashed source files, explicit full-cel/shared-upper registrations, draft exports and human review records.
- `character_workflow.py`: immutable three-view intake, explicit character profile, provider-neutral requests, cel registration, per-view binding and export.
- `layered_motion.py`: explicit authored layers/poses, bounded socket blending and support-only fitting, distinct from the editor's rig format.
- `production_audit.py`, `repair_audit.py`: read-only invariants and diagnostics, never artistic acceptance.
- `synthetic_profiles.py`: multiple original code-drawn technical fixtures.

Preserve a fixed canvas and constant reference scale throughout a loop. Imported source/evidence hashes make stale inputs visible, but do not establish rights, identity or correctness. Some paths use local mesh deformation, so “all pixels remain rigid” is not a valid blanket claim. Imported art and private project coordinates belong in separate production workspaces.

The editor normalizes user input to a 384px canvas. The authored-cel and layered routes use their declared canvas sizes. Front/back projection helpers are manually calibrated 2D models. They cannot infer perspective from a picture or guarantee coherent visible depth without actual image review.

- `dash_registration.py`: parameterized monotone body-axis registration, integer shared-layer placement, shaft/hand and row-width geometry; no image inference.
- `dash_project.py`: source-pinned per-view authored dash registration, PNG/GIF export, diagnostics and byte-exact verification in a clean temporary directory. See `DASH_REPRODUCTION.md` for input constraints and unreviewed temporal status.
- `pose_review.py`: hash-bound per-frame/physical-arm review coverage plus explicitly annotated geometric diagnostics. It does not infer anatomy, hand surfaces, support roles or review outcomes. See `POSE_REVIEW.md`.
