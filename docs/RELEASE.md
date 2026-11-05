# Clean source release

1. Keep artwork, saved editor projects, generated cels, logs and review media in a separate workspace. Only original code-native diagrams are suitable as public test fixtures without additional rights checks.
2. Run all README checks on the exact candidate. Generate demos into ignored `output/`, not tracked examples. Record what was and was not actually observed.
3. Run `python scripts/check_public_release.py`. Review its allowlist and every staged file yourself. A pattern scan can miss personal data and cannot establish asset rights.
4. Inspect `git diff --cached`, `git ls-files` and history. An ignored or later-deleted secret remains in old commits. Use a fresh initial repository for a sanitized first release; never push a private production directory's history.
5. Verify the intended owner, repository and visibility before pushing. Do not include a personal author email in commit metadata unless explicitly intended; use the configured privacy-preserving identity.
6. Verify the exact commit on the remote and its CI result. Publishing source does not deploy the local server or certify the demo's animation quality.

An optional source ZIP can be built with `python scripts/build_release.py --output dist/sprite-motion-lab-source.zip`. It contains only the checked text-source allowlist, no generated outputs or private projects. Inspect the extracted archive and rerun checks there before distribution.
