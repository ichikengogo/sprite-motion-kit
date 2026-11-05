# Dependency inventory

Dependencies are installed separately, not vendored or redistributed in this source repository.

| Dependency | Use | License | Tested locally |
| --- | --- | --- | --- |
| Python 3.10+ | Runtime and standard library | PSF | 3.12 |
| Pillow | Image decoding, drawing, compositing, transforms, PNG/GIF | MIT-CMU (package metadata) | 12.3.0 |
| NumPy | Mesh rasterization and diagnostics | BSD-3-Clause | 2.3.5 |
| Node.js 18+ | Optional JavaScript unit/syntax tests only | Node.js distribution notices | See CI |
| Browser platform APIs | Local editor | Browser distribution notices | No JS library bundled |

The declared ranges allow compatible available releases. They are not a complete reproducible environment lock or a vulnerability audit. Record exact versions when producing assets that need byte-for-byte reproduction; codec/library upgrades can change encoded files even when RGBA pixels match.

Pillow/NumPy wheels can include separately licensed codecs or numerical libraries. If you bundle binaries in an application, include the notices from those exact distributions. No model weights, animation frameworks, downloaded browser binaries, fonts, or copied third-party source are included here. Public research links in the documentation are citations, not redistributed content.
