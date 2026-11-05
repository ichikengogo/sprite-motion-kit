# Contributing

Use original synthetic shapes for tests. Do not commit private or unclear-license artwork, saved browser projects, contact sheets from real characters, absolute workstation paths, cloud upload receipts, credentials, or recorded user conversations. Adding a private directory to `.gitignore` does not remove it from Git history.

Run the Python suite and the Node test files listed in README. For rendering changes, test source immutability, supported views, physical identities, full-cycle/loop continuity, clipping, alpha joins, timing, deterministic reloading and scope of unchanged output. New geometric tests are diagnostics, not evidence that a person's character looks natural.

For a visual-quality claim, review actual RGBA frames on contrasting backgrounds and observe the exact animation at 1x speed at native and intended small size. Record the method, artifact hash, observed loops and concrete findings. Leave temporal quality unreviewed when playback was not actually observed.

New art fixtures need an explicit provenance/license statement. Keep runtime offline; remote-provider integration, if proposed, must be opt-in and clearly separate from local rendering. Never silently send imported artwork to a provider.

Before publishing, run `python scripts/check_public_release.py` and independently inspect the exact staged Git diff/file list. The scanner is a limited pattern and file-type guard, not proof that no personal information exists. Confirm the remote contains only the reviewed initial history. See `docs/RELEASE.md`.
