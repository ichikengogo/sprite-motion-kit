"""Read-only ownership and temporal diagnostics. Never an aesthetic approval gate."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image


def ownership_report(source, layers, alpha_threshold=1):
    """Compare registered neutral alpha, including contour pixels, without changing it.

    Overlap is reported, not rejected: hidden socket/cloth overlap is often needed.
    This cannot determine whether an opaque pixel belongs to the correct body part.
    """
    if not 1 <= alpha_threshold <= 255:
        raise ValueError('alpha_threshold must be 1..255')
    if not layers or any(im.size != source.size for im in layers.values()):
        raise ValueError('Need named layers on the source canvas')
    original = np.asarray(source.convert('RGBA'))[..., 3] >= alpha_threshold
    masks = np.stack([np.asarray(im.convert('RGBA'))[..., 3] >= alpha_threshold for im in layers.values()])
    counts = masks.sum(axis=0)
    omitted = original & (counts == 0)
    extra = ~original & (counts > 0)
    overlap = counts > 1
    overlay = np.zeros((*original.shape, 4), dtype=np.uint8)
    overlay[omitted] = (255, 0, 255, 255)
    overlay[extra] = (0, 255, 255, 255)
    overlay[overlap] = (255, 190, 0, 255)
    return {
        'schema': 'neutral-ownership-audit/1',
        'sourcePixels': int(original.sum()), 'omittedSourcePixels': int(omitted.sum()),
        'addedPixels': int(extra.sum()), 'overlapPixels': int(overlap.sum()),
        'layerPixels': {name: int(mask.sum()) for name, mask in zip(layers, masks)},
        'alphaThreshold': alpha_threshold, 'visualApproval': False,
        'limitations': ['Neutral coverage is not dynamic attachment.',
                       'No semantic ownership, garment or anatomy recognition is performed.',
                       'Overlap may be intentional; zero overlap is not an animation goal.'],
    }, Image.fromarray(overlay)


def _durations(values, count):
    if not isinstance(values, list) or len(values) != count or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in values):
        raise ValueError('One finite positive duration in milliseconds per frame required')
    return np.asarray(values, dtype=float) / 1000


def audit_tracks(tracks, durations_ms):
    """Report actual consecutive and last-to-first displacement and speed.

    Inputs are explicitly authored/measured landmarks; there is no image tracking.
    Body-axis and support changes need interpretation in the declared projection.
    """
    if not isinstance(tracks, dict) or not tracks:
        raise ValueError('Named 2D tracks required')
    report = {}
    for name, values in tracks.items():
        points = np.asarray(values, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3 or not np.isfinite(points).all():
            raise ValueError('Each track needs at least three finite 2D points')
        dt = _durations(durations_ms, len(points))
        steps = np.roll(points, -1, axis=0) - points
        velocity = steps / dt[:, None]
        speed = np.linalg.norm(velocity, axis=1)
        acceleration = (np.roll(velocity, -1, axis=0) - velocity) / dt[:, None]
        report[name] = {'stepPixels': np.linalg.norm(steps, axis=1).tolist(),
                        'speedPixelsPerSecond': speed.tolist(),
                        'accelerationPixelsPerSecondSquared': np.linalg.norm(acceleration, axis=1).tolist(),
                        'lastToFirstSpeed': float(speed[-1]),
                        'zeroStepIndices': np.where(np.all(steps == 0, axis=1))[0].tolist()}
    return {'schema': 'cycle-track-audit/1', 'tracks': report, 'visualApproval': False,
            'limitations': ['No universal speed threshold is imposed.',
                           'In-place stance travel is not automatically sliding.',
                           'Numbers cannot establish intended support, correct depth cues or natural motion.']}


def audit_frames(paths, durations_ms):
    paths = [Path(p) for p in paths]
    if len(paths) < 3:
        raise ValueError('At least three ordered frames required')
    _durations(durations_ms, len(paths))
    hashes = []
    size = None
    for path in paths:
        with Image.open(path) as image:
            image = image.convert('RGBA')
            if size is not None and image.size != size:
                raise ValueError('Frame canvas changed; never fit each frame independently')
            size = image.size
            hashes.append(hashlib.sha256(image.tobytes()).hexdigest())
    repeated = [i for i in range(len(paths)) if hashes[i] == hashes[(i+1) % len(paths)]]
    return {'schema': 'cycle-frame-audit/1', 'frames': len(paths), 'canvas': list(size),
            'rgbaHashes': hashes, 'adjacentIdenticalIndices': repeated,
            'lastEqualsFirst': hashes[-1] == hashes[0],
            'durationMs': sum(durations_ms), 'visualApproval': False,
            'limitations': ['Identical frames may be intentional holds; investigate rather than auto-reject.',
                           'Different hashes do not prove a genuinely opposite half-cycle.',
                           'Static pixels and timing metadata are not observed playback.']}


def validate_temporal_record(record, artifact):
    """Check a hash-bound human assertion, never assert the claimed viewing occurred."""
    required = {'reviewer', 'methodTool', 'artifactSha256', 'speed', 'nativeCompleteLoopsObserved',
                'smallCompleteLoopsObserved', 'smallSizePx', 'continuityFindings', 'outcome', 'unresolvedDefects'}
    if not isinstance(record, dict) or not required.issubset(record):
        raise ValueError('Incomplete temporal evidence record')
    digest = hashlib.sha256(Path(artifact).read_bytes()).hexdigest()
    if record['artifactSha256'] != digest:
        raise ValueError('Temporal evidence is stale or references another artifact')
    if record['outcome'] not in {'accepted', 'rejected', 'unreviewed', 'blocked'}:
        raise ValueError('Unknown temporal outcome')
    if not isinstance(record['unresolvedDefects'], list):
        raise ValueError('unresolvedDefects must be a list')
    if record['outcome'] in {'accepted', 'rejected'}:
        if record['speed'] != 1 or any(type(record[k]) is not int or record[k] < 1 for k in ('nativeCompleteLoopsObserved', 'smallCompleteLoopsObserved', 'smallSizePx')):
            raise ValueError('Observed outcomes need real 1x loop counts at both sizes')
        for key in ('reviewer', 'methodTool', 'continuityFindings'):
            if not isinstance(record[key], str) or not record[key].strip():
                raise ValueError('Observed outcomes need a reviewer, method and concrete findings')
        if record['outcome'] == 'accepted' and record['unresolvedDefects']:
            raise ValueError('Do not accept an artifact with unresolved defects')
    else:
        if any(record[k] is not None for k in ('nativeCompleteLoopsObserved', 'smallCompleteLoopsObserved')):
            raise ValueError('Do not guess loop counts when review is blocked/unreviewed')
    return {'schema': 'temporal-record-validation/1', 'recordStructurallyValid': True,
            'recordedOutcome': record['outcome'], 'artifactSha256': digest,
            'playbackIndependentlyVerified': False, 'visualApproval': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    f = sub.add_parser('frames'); f.add_argument('directory'); f.add_argument('--durations', required=True); f.add_argument('--out', required=True)
    t = sub.add_parser('tracks'); t.add_argument('input'); t.add_argument('--out', required=True)
    r = sub.add_parser('temporal'); r.add_argument('record'); r.add_argument('artifact'); r.add_argument('--out', required=True)
    a = p.parse_args()
    if a.command == 'frames':
        result = audit_frames(sorted(Path(a.directory).glob('frame-*.png')), json.loads(Path(a.durations).read_text()))
    elif a.command == 'tracks':
        data = json.loads(Path(a.input).read_text()); result = audit_tracks(data['tracks'], data['durationsMs'])
    else:
        result = validate_temporal_record(json.loads(Path(a.record).read_text()), a.artifact)
    Path(a.out).write_text(json.dumps(result, indent=2) + '\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
