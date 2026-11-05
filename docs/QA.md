# What is and is not tested

The automated suites use original synthetic diagrams and generated local files. They cover API validation, source and review hashes, physical ownership contracts, constant dimensions, phase/timing metadata, bone/mesh constraints, scoped repairs, loop wrapping, editor playback timing and saved-project loading. Run the exact commands in the root README; CI executes the same checks on a clean checkout.

The synthetic character workflow uses different canvas shapes, proportions, clothing, contact modes, frame counts and all three views. This establishes that the pipeline is not merely replaying a single character JSON. It does **not** establish reliable segmentation, anatomy inference, hidden-surface generation or first-pass artistic success on unseen art.

The layered route tests explicit inputs and mathematical invariants. The newer production diagnostics report full neutral alpha coverage (including faint outlines), overlap separately from omissions, actual duration-based movement and last-to-first comparisons. They do not recognize the semantic owner of a pixel.

Node playback tests simulate different refresh rates, pause/resume and seeking. They do not constitute visual inspection in a real browser. Python HTTP integration verifies requests and responses, not perceived smoothness. Local browser/manual interaction and continuous video observation must be reported separately when actually performed.

No automated test marks artwork accepted. A structural temporal-review record is a hash-bound human assertion, not proof that its observations happened. An unobserved animation remains UNREVIEWED even if every numerical test passes. Known identity jitter, disconnected anatomy and implausible support transitions must not be dismissed as a generic prototype limitation when claiming a finished result.
