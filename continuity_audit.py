"""Authored opaque-region and backing-layer diagnostics, never an art judge.

No anatomy, hair, straps, fists, negative space, or occlusion is inferred. Inputs
are actual still images at one canvas/scale, with explicit binary L/1 masks.
See docs/CONTINUITY_REPAIRS.md for whole-component and foreground ownership checks.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def _rgba(image):
    if not isinstance(image, Image.Image) or getattr(image, 'n_frames', 1) != 1:
        raise ValueError('Use actual still PIL images, not encoded animations')
    return np.array(image.convert('RGBA'))


def _mask(image, shape, label, nonempty=True):
    if (not isinstance(image, Image.Image) or image.mode not in ('1', 'L')
            or getattr(image, 'n_frames', 1) != 1):
        raise ValueError(f'{label} must be a binary L/1 still image')
    data = np.array(image.convert('L'))
    if data.shape != shape or np.any((data != 0) & (data != 255)):
        raise ValueError(f'{label} must match the canvas and contain only 0/255')
    result = data == 255
    if nonempty and not result.any():
        raise ValueError(f'{label} must select at least one pixel')
    return result


def _hash(array):
    """Decoded-array identity, not a hash of encoded PNG bytes or a review record."""
    header = json.dumps({'shape': list(array.shape), 'dtype': str(array.dtype)},
                        sort_keys=True).encode('ascii')
    return hashlib.sha256(header + b'\0' + array.tobytes()).hexdigest()


def _report(kind):
    return {'schema': 'continuity-audit/1', 'kind': kind,
            'visualApproval': False, 'temporalReview': 'UNREVIEWED',
            'hashScope': 'decoded arrays, shape and dtype; not encoded file bytes',
            'limitations': [
                'Masks, registration, expected artwork and occlusion are authored claims.',
                'Pixel equality does not prove face direction, anatomy, ownership or natural motion.',
                'Inspect mask scope, complete contours, all actual cels and exact playback separately.']}


def registered_region(reference, candidate, region_mask, offset=(0, 0), occluder_mask=None):
    """Compare an authored opaque region after one integer reference-to-output shift.

    region_mask is in reference coordinates; occluder_mask is in candidate
    coordinates and names foreground pixels intentionally hiding this region.
    Only opaque reference pixels can be selected, so antialiased edges require
    separate composite/visual review. No automatic alignment, wrapping, clipping,
    resizing, color thresholds or tolerance is applied. A fully hidden region
    returns matches=None (unmeasured), never a successful equality assertion.
    """
    source, actual = _rgba(reference), _rgba(candidate)
    if source.shape != actual.shape:
        raise ValueError('Reference and candidate must share one canvas')
    region = _mask(region_mask, source.shape[:2], 'region_mask')
    if np.any(source[:, :, 3][region] != 255):
        raise ValueError('Region must select opaque reference pixels only')
    if (not isinstance(offset, (list, tuple)) or len(offset) != 2
            or any(type(value) is not int for value in offset)):
        raise ValueError('offset must be two integer pixel translations')
    dx, dy = offset
    y, x = np.where(region)
    height, width = region.shape
    if (int(x.min()) + dx < 0 or int(x.max()) + dx >= width
            or int(y.min()) + dy < 0 or int(y.max()) + dy >= height):
        raise ValueError('Translated region leaves canvas; clipping would hide a defect')
    tx, ty = x + dx, y + dy
    occluder = (np.zeros(region.shape, dtype=bool) if occluder_mask is None
                else _mask(occluder_mask, region.shape, 'occluder_mask', nonempty=False))
    visible = ~occluder[ty, tx]
    expected, found = source[y[visible], x[visible]], actual[ty[visible], tx[visible]]
    changed = np.any(expected != found, axis=1)
    alpha = found[:, 3]
    count = int(visible.sum())
    return {**_report('registered-opaque-region'), 'offset': list(offset),
            'referencePixels': int(region.sum()), 'visiblePixels': count,
            'occludedPixels': int((~visible).sum()), 'changedPixels': int(changed.sum()),
            'missingTransparentPixels': int((alpha == 0).sum()),
            'partialAlphaPixels': int(((alpha > 0) & (alpha < 255)).sum()),
            'changedOpaquePixels': int((changed & (alpha == 255)).sum()),
            'matches': bool(not changed.any()) if count else None,
            'measurementStatus': 'MEASURED' if count else 'FULLY_OCCLUDED',
            'inputs': {'reference': _hash(source), 'candidate': _hash(actual),
                       'regionMask': _hash(region), 'occluderMask': _hash(occluder)}}


def backing_preservation(before, after, allowed_reveal_mask):
    """Check local backing repair preserves opaque foreground and outside scope.

    Transparent/partial pixels inside allowed_reveal_mask may gain opacity and
    color from the backing layer. Alpha must never decrease. This does not prove
    the hole was filled or that the fill depicts the right material; also inspect
    its complete expected layer with registered_region and the actual composite.
    """
    old, new = _rgba(before), _rgba(after)
    if old.shape != new.shape:
        raise ValueError('Before and after must share one canvas')
    scope = _mask(allowed_reveal_mask, old.shape[:2], 'allowed_reveal_mask')
    changed = np.any(old != new, axis=2)
    opaque_changed = int((changed & (old[:, :, 3] == 255)).sum())
    outside = int((changed & ~scope).sum())
    decreased = int((new[:, :, 3] < old[:, :, 3]).sum())
    return {**_report('backing-preservation'),
            'changedPixels': int(changed.sum()), 'outsideAllowedPixels': outside,
            'opaqueForegroundChangedPixels': opaque_changed,
            'alphaDecreasedPixels': decreased,
            'gainedAlphaPixels': int((new[:, :, 3] > old[:, :, 3]).sum()),
            'allowedFraction': float(scope.mean()),
            'invariantsPass': not (opaque_changed or outside or decreased),
            'inputs': {'before': _hash(old), 'after': _hash(new), 'allowedMask': _hash(scope)}}


def demo(output):
    """Generate only original geometric fixtures with deliberate failures."""
    root = Path(output)
    if root.exists() or root.is_symlink():
        raise ValueError('Use a new output directory')
    root.mkdir(parents=True)
    source = Image.new('RGBA', (64, 64))
    draw = ImageDraw.Draw(source)
    draw.rectangle((24, 8, 39, 22), fill=(80, 100, 150, 255))
    draw.rectangle((28, 23, 34, 51), fill=(50, 70, 90, 255))
    region = source.getchannel('A')
    moved = Image.new('RGBA', source.size)
    moved.alpha_composite(source, (0, 2))
    occluder = Image.new('L', source.size)
    ImageDraw.Draw(occluder).rectangle((26, 30, 37, 37), fill=255)
    correct = moved.copy()
    ImageDraw.Draw(correct).rectangle((26, 30, 37, 37), fill=(175, 130, 95, 255))
    missing = correct.copy()
    ImageDraw.Draw(missing).rectangle((28, 44, 34, 53), fill=(0, 0, 0, 0))
    white = correct.copy()
    ImageDraw.Draw(white).rectangle((29, 40, 32, 43), fill=(255, 255, 255, 255))
    files = {'reference': source, 'region-mask': region, 'occluder-mask': occluder,
             'correct': correct, 'missing-lower-component': missing, 'opaque-repaint': white}
    for name, image in files.items():
        image.save(root / f'{name}.png')
    cases = {name: registered_region(source, image, region, (0, 2), occluder)
             for name, image in [('correct', correct), ('missing-lower-component', missing),
                                  ('opaque-repaint', white)]}
    report = {'syntheticOnly': True, 'visualApproval': False, 'temporalReview': 'UNREVIEWED',
              'cases': cases, 'expectedResultsObserved': (
                  cases['correct']['matches'] is True
                  and cases['missing-lower-component']['missingTransparentPixels'] > 0
                  and cases['opaque-repaint']['changedOpaquePixels'] > 0
                  and cases['opaque-repaint']['missingTransparentPixels'] == 0)}
    (root / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('demo', help='Write original geometric diagnostic fixtures')
    command.add_argument('output')
    args = parser.parse_args(argv)
    try:
        report = demo(args.output)
        print(json.dumps(report, indent=2))
        return 0 if report['expectedResultsObserved'] else 1
    except (ValueError, OSError) as error:
        print(json.dumps({'error': str(error), 'visualApproval': False,
                          'temporalReview': 'UNREVIEWED'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
