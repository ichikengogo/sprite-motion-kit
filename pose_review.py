"""Source-bound, per-authored-frame hand/pose review, NOT visual certification.

Commands (all paths are relative to --root, including manifest image paths)::

    python pose_review.py --root output/pose-demo demo
    python pose_review.py --root output/pose-demo init manifest.json review.json
    python pose_review.py --root output/pose-demo check manifest.json review.json

``demo`` explicitly generates original geometric PNG fixtures, a manifest, and an
UNREVIEWED worksheet. It refuses existing files. No artwork is generated on import.
``init`` consumes pose-review-input/1 JSON (see demo's manifest for a full example):
  view, facing, canvas [width,height], fixedScale, sources [{id,path}],
  physicalArms [{physicalArmId,anatomicalSide}], and ordered frames
  [{id,path,durationMs,phase,armMapping: {armId: {nearFar,screenSide}}}].
A single requested view is sufficient. Anatomical identities persist; near/far
and screen-side mappings are authored per frame, never inferred from a view name.
Anatomical side may be left/right/unknown/not-applicable; nearFar may be
near/far/same-depth/unknown; screenSide may be left/right/center/overlap/unknown.

Each frame is one actual authored PNG cel, not an encoded GIF/APNG frame or a
sample chosen from an animation. Repeated cel paths/holds are allowed with unique
frame IDs and actual positive durations. Phases are explicit nonempty labels;
order is the manifest order, never a filename sort. All actual cels must share the fixed
canvas. Original references retain their own native dimensions, recorded in the
snapshot, and are never resized. fixedScale is a declared, fixed cel scale, NOT
an automatic measurement.
Do not resize individual cels to fit their bounding boxes.

The worksheet contains every frame x physical arm, a complete source snapshot,
and optional per-frame manually authored landmarks. All originals AND cels are
byte-hashed. Any changed source, cel, duration, mapping, phase, scale, or order
invalidates the entire snapshot, including previously RECORDED rows. Re-init and
reinspect; do not copy old observations merely to silence a stale check. Hashes
bind assertions to inputs, not to an authenticated reviewer or proof of viewing.
The manifest must enumerate all relevant source images; undisclosed files cannot
be checked. Paths, including symlinks, must resolve within --root.

Row ``expected`` and ``observed`` fields are authored independently by a reviewer:
  visibility: unknown/visible/partial/occluded
  surface: unknown/palm/back/edge/mixed/occluded
  thumbSide: unknown/toward-body/away-from-body/other/occluded
  thumbTip: unknown/visible/not-visible/occluded
  fistUpRelativeToWrist, fistUpRelativeToBody, forwardThrust:
      unknown/yes/no/not-applicable/occluded
  bodyReference: null or an explicit body-axis/reference description (required
      for yes/no fistUpRelativeToBody; 'up' is relative to that authored reference)
  wristCuff: unknown/continuous/broken/not-applicable/occluded
  fingers: unknown/coherent/incoherent/occluded
A thumb tip is not the thumb SIDE, a thumb cue is not palm/back recognition,
and a raised fist is not forward thrust. There is no universal palm/up rule.
Visibility 'occluded' permits only unknown/occluded assertions; 'visible' cannot
assert occluded fields. Partial visibility permits individual occluded fields.

UNREVIEWED rows may contain authored expectations, but no observed claims.
To record an inspection, set reviewStatus to RECORDED, identify reviewer, provide
concrete findings, and author observed values (unknown/occluded remain honest).
RECORDED means only that an assertion exists, not that the pose matches intent.
check reports schema validity, coverage, freshness and counts. A fresh incomplete
worksheet is structurally valid; --require-recorded additionally requires every
row to be RECORDED. Authored string disagreements and unknown/occluded fields are
reported separately, not treated as fulfilled intent. Neither mode sets
visualApproval or temporalReview to reviewed.
Use production_audit.py for separate exact-artifact playback evidence and
repair_audit.py for pixel-change scope. This tool performs neither operation.

Optional ``landmarks[frameId]`` is null, or {reviewer, pelvis?, arms?, legs?}:
  pelvis: [x,y]
  arms: {physicalArmId: {shoulder:[x,y], elbow:[x,y], wrist:[x,y],
                        handMaskPixels?: [[integer_x,integer_y], ...]}}
  legs: {physicalLegId: {phase: support/recovery/unknown,
                        hip:[x,y], knee:[x,y], ankle:[x,y]}}
Coordinates are explicitly authored in canvas pixels (x right, y down). Integer
mask coordinates name pixels; their centers are (x+.5,y+.5). No segmentation or
tracking occurs. Diagnostics report arm lengths, hand-mask area, exclusive bounds
and centroid/offset about wrist, pelvis y, knee angle and hip-to-ankle reach per
DECLARED leg phase. All landmarks must be finite/in-canvas and segments nonzero;
no anatomical thresholds or inferred support are imposed. Missing landmarks are
unmeasured, never silently zero. Numbers cannot certify believable anatomy/gait.

API ``tracked_region_sheet(images, anchors, crop_size, zoom, columns=4)`` returns
an ordered RGBA sheet of fixed-size crops centered on authored integer anchors
(e.g. wrists). Images must share one canvas; one crop size and integer nearest-
neighbor zoom apply to the entire sheet. Overflow is transparently padded, never
fitted to a per-frame bounding box. Apply the same settings to before/after inputs
for comparable scale. Anchors are not detected and the sheet is static evidence,
not playback review.
"""
import argparse
import copy
import hashlib
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

INPUT_SCHEMA = 'pose-review-input/1'
REVIEW_SCHEMA = 'pose-review/1'
SEMANTIC_CHOICES = {
    'visibility': {'unknown', 'visible', 'partial', 'occluded'},
    'surface': {'unknown', 'palm', 'back', 'edge', 'mixed', 'occluded'},
    'thumbSide': {'unknown', 'toward-body', 'away-from-body', 'other', 'occluded'},
    'thumbTip': {'unknown', 'visible', 'not-visible', 'occluded'},
    'fistUpRelativeToWrist': {'unknown', 'yes', 'no', 'not-applicable', 'occluded'},
    'fistUpRelativeToBody': {'unknown', 'yes', 'no', 'not-applicable', 'occluded'},
    'forwardThrust': {'unknown', 'yes', 'no', 'not-applicable', 'occluded'},
    'wristCuff': {'unknown', 'continuous', 'broken', 'not-applicable', 'occluded'},
    'fingers': {'unknown', 'coherent', 'incoherent', 'occluded'},
}


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be nonempty text')
    return value


def _number(value, label, positive=False):
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or (positive and value <= 0):
        raise ValueError(f'{label} must be finite' + (' and positive' if positive else ''))
    return value


def _fields(value, required, label, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise ValueError(f'{label} has missing or unknown fields; required: {", ".join(sorted(required))}')


def _choice(value, allowed, label):
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f'{label} must be one of {", ".join(sorted(allowed))}')


def _canvas(value):
    if not isinstance(value, list) or len(value) != 2 or any(type(n) is not int or n <= 0 for n in value):
        raise ValueError('canvas must contain two positive integer dimensions')
    return value


def confined_path(root, relative):
    """Resolve a project-relative path; reject absolute/traversal/symlink escapes."""
    _text(relative, 'path')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Paths must be project-relative without parent traversal')
    root = Path(root).resolve()
    resolved = (root / path).resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError('Path escapes project root')
    return resolved


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def _unique_ids(items, key, label):
    if not isinstance(items, list) or not items:
        raise ValueError(f'{label} must be a nonempty list')
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f'{label} entries must be objects')
        value = _text(item.get(key), f'{label}.{key}')
        if value in seen:
            raise ValueError(f'Duplicate {label} {key}: {value}')
        seen.add(value)
    return seen


def _validate_manifest(manifest):
    _fields(manifest, {'schema', 'view', 'facing', 'canvas', 'fixedScale', 'sources',
                       'physicalArms', 'frames'}, 'manifest')
    if manifest['schema'] != INPUT_SCHEMA:
        raise ValueError(f'Expected {INPUT_SCHEMA}')
    for field in ('view', 'facing'):
        _text(manifest[field], field)
    canvas = _canvas(manifest['canvas'])
    _number(manifest['fixedScale'], 'fixedScale', positive=True)
    _unique_ids(manifest['sources'], 'id', 'sources')
    arm_ids = _unique_ids(manifest['physicalArms'], 'physicalArmId', 'physicalArms')
    _unique_ids(manifest['frames'], 'id', 'frames')
    for arm in manifest['physicalArms']:
        _fields(arm, {'physicalArmId', 'anatomicalSide'}, 'physicalArm')
        _choice(arm['anatomicalSide'], {'left', 'right', 'unknown', 'not-applicable'}, 'anatomicalSide')
    for source in manifest['sources']:
        _fields(source, {'id', 'path'}, 'source')
    for frame in manifest['frames']:
        _fields(frame, {'id', 'path', 'durationMs', 'phase', 'armMapping'}, 'frame')
        _number(frame['durationMs'], 'durationMs', positive=True)
        _text(frame['phase'], 'phase')
        mapping = frame['armMapping']
        if not isinstance(mapping, dict) or set(mapping) != arm_ids:
            raise ValueError('Every frame needs armMapping for every physical arm')
        for arm in mapping.values():
            _fields(arm, {'nearFar', 'screenSide'}, 'armMapping')
            _choice(arm['nearFar'], {'near', 'far', 'same-depth', 'unknown'}, 'nearFar')
            _choice(arm['screenSide'], {'left', 'right', 'center', 'overlap', 'unknown'}, 'screenSide')
    _number(sum(f['durationMs'] for f in manifest['frames']), 'total durationMs', positive=True)
    return canvas


def source_snapshot(manifest, root):
    """Validate an authored manifest and hash exact source PNG bytes and context."""
    canvas = _validate_manifest(manifest)
    files = []
    for kind, images in (('source', manifest['sources']), ('frame', manifest['frames'])):
        for item in images:
            path = confined_path(root, item['path'])
            raw = path.read_bytes()
            # Hash and decode the same bytes, not two possibly different reads.
            with Image.open(io.BytesIO(raw)) as image:
                if image.format != 'PNG' or getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('Use actual single-frame PNG cels, not encoded animation frames')
                if kind == 'frame' and list(image.size) != canvas:
                    raise ValueError('Fixed canvas changed; never fit each frame independently')
                image.load()
                size = list(image.size)
            files.append({'kind': kind, 'id': item['id'], 'path': item['path'],
                          'sha256': hashlib.sha256(raw).hexdigest(), 'canvas': size})
    return {'manifest': copy.deepcopy(manifest), 'files': files}


def unknown_semantics():
    """Return new independent fields; no source-level intent becomes an observation."""
    return {**{field: 'unknown' for field in SEMANTIC_CHOICES}, 'bodyReference': None}


def init_review(manifest, root):
    """Create an entirely UNREVIEWED, source/hash-bound worksheet for one view."""
    snapshot = source_snapshot(manifest, root)
    rows = []
    for frame in manifest['frames']:
        for arm in manifest['physicalArms']:
            arm_id = arm['physicalArmId']
            rows.append({'frameId': frame['id'], 'physicalArmId': arm_id,
                         'phase': frame['phase'], 'mapping': copy.deepcopy(frame['armMapping'][arm_id]),
                         'expected': unknown_semantics(), 'observed': unknown_semantics(),
                         'reviewStatus': 'UNREVIEWED', 'reviewer': None, 'findings': None})
    return {'schema': REVIEW_SCHEMA, 'sourceSetSha256': _digest(snapshot), 'snapshot': snapshot,
            'rows': rows, 'landmarks': {f['id']: None for f in manifest['frames']},
            'visualApproval': False, 'temporalReview': 'UNREVIEWED'}


def _semantics(value, label):
    _fields(value, set(SEMANTIC_CHOICES) | {'bodyReference'}, label)
    for key, allowed in SEMANTIC_CHOICES.items():
        _choice(value[key], allowed, f'{label}.{key}')
    if value['bodyReference'] is not None:
        _text(value['bodyReference'], f'{label}.bodyReference')
    if value['fistUpRelativeToBody'] in {'yes', 'no'} and value['bodyReference'] is None:
        raise ValueError(f'{label}: bodyReference required for body-relative fist direction')
    claims = [value[k] for k in SEMANTIC_CHOICES if k != 'visibility']
    if value['visibility'] in {'unknown', 'occluded'} and any(v not in {'unknown', 'occluded'} for v in claims):
        raise ValueError(f'{label}: unknown/occluded visibility contradicts visible assertions')
    if value['visibility'] == 'visible' and 'occluded' in claims:
        raise ValueError(f'{label}: visible hand contradicts occluded assertions; use partial')


def _point(value, canvas, label, integer=False):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f'{label} must be a 2D point')
    for index, component in enumerate(value):
        _number(component, label)
        if integer and type(component) is not int:
            raise ValueError(f'{label} requires integer pixel indices')
        maximum = canvas[index] - 1 if integer else canvas[index]
        if not 0 <= component <= maximum:
            raise ValueError(f'{label} is outside canvas')
    return value


def _distance(a, b):
    distance = math.hypot(b[0] - a[0], b[1] - a[1])
    if not math.isfinite(distance):
        raise ValueError('Landmark distance must be finite')
    return distance


def _chain(item, names, canvas):
    points = [_point(item[name], canvas, name) for name in names]
    lengths = [_distance(points[i], points[i+1]) for i in range(2)]
    if any(length == 0 for length in lengths):
        raise ValueError('Degenerate zero-length landmark segment')
    return points, lengths


def landmark_diagnostics(record, canvas, arm_ids):
    """Report authored geometry without thresholds, image tracking or support inference.

    This low-level API is not independently source-bound. check_review binds its
    output to the complete source snapshot and withholds metrics when stale.
    """
    _canvas(canvas)
    _fields(record, {'reviewer'}, 'landmarks', {'pelvis', 'arms', 'legs'})
    _text(record['reviewer'], 'landmarks.reviewer')
    if len(record) == 1:
        raise ValueError('Provide landmarks or leave the frame null, not an empty measurement')
    result = {'reviewer': record['reviewer'], 'coordinateSystem': 'pixels-x-right-y-down',
              'visualApproval': False, 'automaticSupportInference': False}
    if 'pelvis' in record:
        result['pelvisY'] = _point(record['pelvis'], canvas, 'pelvis')[1]
    if 'arms' in record:
        if not isinstance(record['arms'], dict) or not record['arms'] or not set(record['arms']) <= set(arm_ids):
            raise ValueError('Measured arms must be nonempty and refer to declared physical arms')
        result['arms'] = {}
        for arm_id, arm in record['arms'].items():
            _fields(arm, {'shoulder', 'elbow', 'wrist'}, 'arm landmarks', {'handMaskPixels'})
            points, lengths = _chain(arm, ('shoulder', 'elbow', 'wrist'), canvas)
            measured = {'upperArmPixels': lengths[0], 'forearmPixels': lengths[1],
                        'shoulderWristReachPixels': _distance(points[0], points[2])}
            if 'handMaskPixels' in arm:
                pixels = arm['handMaskPixels']
                if not isinstance(pixels, list) or not pixels:
                    raise ValueError('handMaskPixels must be a nonempty authored pixel mask')
                checked = [tuple(_point(p, canvas, 'handMaskPixels', integer=True)) for p in pixels]
                if len(set(checked)) != len(checked):
                    raise ValueError('handMaskPixels contains duplicate pixels')
                xs, ys = zip(*checked)
                centroid = [sum(xs) / len(xs) + .5, sum(ys) / len(ys) + .5]
                wrist = points[2]
                measured['handMask'] = {
                    'areaPixels': len(checked), 'boundsExclusive': [min(xs), min(ys), max(xs)+1, max(ys)+1],
                    'centroid': centroid, 'centroidFromWrist': [centroid[0]-wrist[0], centroid[1]-wrist[1]],
                    'centroidDistanceFromWristPixels': _distance(wrist, centroid)}
            result['arms'][arm_id] = measured
    if 'legs' in record:
        if not isinstance(record['legs'], dict) or not record['legs']:
            raise ValueError('Measured legs must be a nonempty object')
        result['legs'] = {}
        for leg_id, leg in record['legs'].items():
            _text(leg_id, 'physical leg ID')
            _fields(leg, {'phase', 'hip', 'knee', 'ankle'}, 'leg landmarks')
            _choice(leg['phase'], {'support', 'recovery', 'unknown'}, 'declared leg phase')
            points, lengths = _chain(leg, ('hip', 'knee', 'ankle'), canvas)
            hip, knee, ankle = points
            # Unit vectors avoid overflowing the product of squared lengths.
            u = [(hip[i]-knee[i])/lengths[0] for i in range(2)]
            v = [(ankle[i]-knee[i])/lengths[1] for i in range(2)]
            angle = math.degrees(math.acos(max(-1, min(1, sum(a*b for a, b in zip(u, v))))))
            reach = _distance(hip, ankle)
            total = _number(sum(lengths), 'leg segment sum', positive=True)
            result['legs'][leg_id] = {'declaredPhase': leg['phase'], 'thighPixels': lengths[0],
                                     'shinPixels': lengths[1], 'hipKneeAnkleDegrees': angle,
                                     'hipAnkleReachPixels': reach, 'reachOverSegmentSum': reach/total}
    return result


def check_review(manifest, worksheet, root, require_recorded=False):
    """Validate coverage/claims; report stale records, never certify their semantics.

    Malformed data raises ValueError. Well-formed but stale/incomplete input yields
    checkPassed=False when stale, or when require_recorded and rows are unreviewed.
    Even checkPassed=True leaves visualApproval=False and temporalReview=UNREVIEWED.
    """
    current = source_snapshot(manifest, root)
    _fields(worksheet, {'schema', 'sourceSetSha256', 'snapshot', 'rows', 'landmarks',
                        'visualApproval', 'temporalReview'}, 'worksheet')
    if worksheet['schema'] != REVIEW_SCHEMA:
        raise ValueError(f'Expected {REVIEW_SCHEMA}')
    if worksheet['visualApproval'] is not False or worksheet['temporalReview'] != 'UNREVIEWED':
        raise ValueError('A pose worksheet cannot assert visualApproval or temporal review')
    snapshot = worksheet['snapshot']
    _fields(snapshot, {'manifest', 'files'}, 'snapshot')
    bound = snapshot['manifest']
    _validate_manifest(bound)
    expected_files = [(kind, item) for kind, items in (('source', bound['sources']), ('frame', bound['frames']))
                      for item in items]
    if not isinstance(snapshot['files'], list) or len(snapshot['files']) != len(expected_files):
        raise ValueError('Snapshot must hash every source and authored frame')
    for file_record, (kind, item) in zip(snapshot['files'], expected_files):
        _fields(file_record, {'kind', 'id', 'path', 'sha256', 'canvas'}, 'snapshot file')
        digest = file_record['sha256']
        _canvas(file_record['canvas'])
        if kind == 'frame' and file_record['canvas'] != bound['canvas']:
            raise ValueError('Snapshot frame canvas contradicts bound manifest')
        if (file_record['kind'], file_record['id'], file_record['path']) != (kind, item['id'], item['path']):
            raise ValueError('Snapshot file order/identity contradicts bound manifest')
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid snapshot file SHA-256')
    if worksheet['sourceSetSha256'] != _digest(snapshot):
        raise ValueError('Worksheet source snapshot digest is inconsistent')
    fresh = snapshot == current
    rows = worksheet['rows']
    if not isinstance(rows, list):
        raise ValueError('rows must be a list')
    required = {(f['id'], a['physicalArmId']): f for f in bound['frames'] for a in bound['physicalArms']}
    seen, recorded, unreviewed = set(), [], []
    differences, unresolved = [], []
    for row in rows:
        _fields(row, {'frameId', 'physicalArmId', 'phase', 'mapping', 'expected', 'observed',
                      'reviewStatus', 'reviewer', 'findings'}, 'row')
        key = (_text(row['frameId'], 'frameId'), _text(row['physicalArmId'], 'physicalArmId'))
        if key not in required or key in seen:
            raise ValueError('Unexpected or duplicate frame/physical-arm row')
        seen.add(key)
        frame = required[key]
        if row['phase'] != frame['phase'] or row['mapping'] != frame['armMapping'][key[1]]:
            raise ValueError('Row phase/mapping contradicts its bound manifest')
        _semantics(row['expected'], 'expected')
        _semantics(row['observed'], 'observed')
        _choice(row['reviewStatus'], {'UNREVIEWED', 'RECORDED'}, 'reviewStatus')
        if row['reviewStatus'] == 'UNREVIEWED':
            if row['observed'] != unknown_semantics() or row['reviewer'] is not None or row['findings'] is not None:
                raise ValueError('UNREVIEWED row cannot contain observations/reviewer/findings')
            unreviewed.append(list(key))
        else:
            _text(row['reviewer'], 'reviewer')
            _text(row['findings'], 'findings')
            recorded.append(list(key))
            # Compare authored strings only. This is not recognition or acceptance.
            fields = [field for field in SEMANTIC_CHOICES
                      if row['expected'][field] not in ({'unknown'} if field == 'visibility' else {'unknown', 'occluded'})
                      and row['observed'][field] not in ({'unknown'} if field == 'visibility' else {'unknown', 'occluded'})
                      and row['expected'][field] != row['observed'][field]]
            if (row['expected']['bodyReference'] is not None and row['observed']['bodyReference'] is not None
                    and row['expected']['bodyReference'] != row['observed']['bodyReference']):
                fields.append('bodyReference')
            if fields:
                differences.append({'frameId': key[0], 'physicalArmId': key[1],
                                    'fields': {field: {'expected': row['expected'][field],
                                                       'observed': row['observed'][field]} for field in fields}})
        unknowns = {'expectedOccluded': [field for field in SEMANTIC_CHOICES if row['expected'][field] == 'occluded'],
                    'expectedUnknown': [field for field in SEMANTIC_CHOICES if row['expected'][field] == 'unknown'],
                    'observedUnknown': [field for field in SEMANTIC_CHOICES if row['observed'][field] == 'unknown'],
                    'observedOccluded': [field for field in SEMANTIC_CHOICES if row['observed'][field] == 'occluded']}
        if any(unknowns.values()):
            unresolved.append({'frameId': key[0], 'physicalArmId': key[1], **unknowns})
    if seen != set(required):
        raise ValueError('Missing frame/physical-arm rows, including required phases')
    landmarks = worksheet['landmarks']
    if not isinstance(landmarks, dict) or set(landmarks) != {f['id'] for f in bound['frames']}:
        raise ValueError('landmarks must contain every actual frame (null means unmeasured)')
    measured = {}
    for frame_id, record in landmarks.items():
        if record is not None:
            measured[frame_id] = landmark_diagnostics(record, bound['canvas'],
                                                      [a['physicalArmId'] for a in bound['physicalArms']])
    complete = fresh and not unreviewed
    current_keys = {(f['id'], a['physicalArmId']) for f in manifest['frames'] for a in manifest['physicalArms']}
    return {'schema': 'pose-review-check/1', 'schemaValid': True,
            'checkScope': 'structure, source freshness and row coverage only; never visual or temporal approval',
            'coverageComplete': seen == current_keys, 'boundCoverageComplete': True,
            'missingCurrentRows': [list(key) for key in sorted(current_keys - seen)],
            'sourceSetFresh': fresh, 'currentSourceSetSha256': _digest(current),
            'authoredFrameCount': len(manifest['frames']), 'encodedFrameCount': None,
            'durationMs': sum(f['durationMs'] for f in manifest['frames']),
            'rowCount': len(rows), 'recordedRowCount': len(recorded),
            'unreviewedRows': unreviewed, 'staleRecordedRows': [] if fresh else recorded,
            'reviewRecordsComplete': complete,
            'authoredAssertionDifferences': differences, 'unresolvedAssertions': unresolved,
            'assertionComparisonOnly': True,
            'checkPassed': fresh and (complete or not require_recorded),
            'landmarkDiagnostics': measured if fresh else None,
            'visualApproval': False, 'automaticSemanticValidation': False,
            'temporalReview': 'UNREVIEWED', 'playbackIndependentlyVerified': False,
            'limitations': ['RECORDED is a reviewer assertion, not visual acceptance.',
                           'Only declared inputs and actual authored frames are checked; no encoded playback is observed.',
                           'Fixed scale, phase, hand semantics and support are authored, not inferred.',
                           'No universal palm, fist-up, anatomical or gait thresholds are applied.']}



def tracked_region_sheet(images, anchors, crop_size, zoom, columns=4):
    """Build constant-scale crops at authored anchors; transparent pad, never fit.

    images are PIL images in actual authored-frame order. anchors are integer
    [x,y] positions on that shared canvas. For an even crop size, the anchor is at
    (width//2,height//2) within the crop. No landmarks or anatomy are inferred.
    """
    if not isinstance(images, (list, tuple)) or not images:
        raise ValueError('Need a nonempty ordered sequence of PIL images')
    if not isinstance(anchors, (list, tuple)) or len(anchors) != len(images):
        raise ValueError('Need one authored integer anchor per actual frame')
    if not isinstance(crop_size, (list, tuple)):
        raise ValueError('crop_size must contain fixed integer width and height')
    width, height = _canvas(list(crop_size))
    if type(zoom) is not int or zoom <= 0 or type(columns) is not int or columns <= 0:
        raise ValueError('zoom and columns must be positive integers')
    if not all(isinstance(image, Image.Image) for image in images):
        raise ValueError('images must contain PIL images')
    canvas = list(images[0].size)
    if any(getattr(image, 'n_frames', 1) != 1 for image in images):
        raise ValueError('Tracked crops require actual still images, not encoded animation frames')
    if any(list(image.size) != canvas for image in images):
        raise ValueError('Fixed canvas changed; tracked crops never refit frames')
    positions = [_point(anchor, canvas, 'anchor', integer=True) for anchor in anchors]
    columns = min(columns, len(images))
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new('RGBA', (columns * width * zoom, rows * height * zoom), (0, 0, 0, 0))
    for index, (image, (x, y)) in enumerate(zip(images, positions)):
        left, top = x - width // 2, y - height // 2
        crop = image.convert('RGBA').crop((left, top, left + width, top + height))
        crop = crop.resize((width * zoom, height * zoom), Image.Resampling.NEAREST)
        sheet.paste(crop, ((index % columns) * width * zoom, (index // columns) * height * zoom))
    return sheet


def _load(root, relative):
    return json.loads(confined_path(root, relative).read_text(encoding='utf-8'))


def _write(root, relative, data):
    target = confined_path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')


def demo(root):
    """Explicitly generate original geometric fixtures; never draw on import/check."""
    root = Path(root)
    names = ['source.png', 'frame-000.png', 'frame-001.png', 'frame-002.png', 'manifest.json', 'review.json']
    targets = [confined_path(root, name) for name in names]
    if len(set(targets)) != len(targets):
        raise ValueError('Demo output paths must be distinct')
    for name in names:
        if confined_path(root, name).exists() or (root / name).is_symlink():
            raise ValueError(f'Refusing to overwrite demo file: {name}')
    root.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(names[:4]):
        im = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        draw.ellipse((37, 8, 59, 30), fill=(70, 115, 160, 255))
        draw.rectangle((36, 31, 60, 60), fill=(50, 100, 150, 255))
        draw.line([(39, 60), (36-index*2, 84)], fill=(65, 85, 105, 255), width=7)
        draw.line([(56, 60), (60+index*2, 84)], fill=(65, 85, 105, 255), width=7)
        draw.line([(35, 34), (22, 47-index*2), (25, 61-index*3)], fill=(125, 165, 195, 255), width=6)
        draw.line([(61, 34), (74, 47+index*2), (71, 61+index*2)], fill=(125, 165, 195, 255), width=6)
        im.save(confined_path(root, name))
    mapping = {'arm-A': {'nearFar': 'unknown', 'screenSide': 'left'},
               'arm-B': {'nearFar': 'unknown', 'screenSide': 'right'}}
    manifest = {'schema': INPUT_SCHEMA, 'view': 'front', 'facing': 'toward-viewer',
                'canvas': [96, 96], 'fixedScale': 1,
                'sources': [{'id': 'original', 'path': 'source.png'}],
                'physicalArms': [{'physicalArmId': 'arm-A', 'anatomicalSide': 'right'},
                                 {'physicalArmId': 'arm-B', 'anatomicalSide': 'left'}],
                'frames': [{'id': f'cel-{i}', 'path': f'frame-{i:03}.png',
                            'durationMs': duration, 'phase': phase, 'armMapping': copy.deepcopy(mapping)}
                           for i, (duration, phase) in enumerate(zip([90, 140, 110], ['start', 'middle', 'end']))]}
    _write(root, 'manifest.json', manifest)
    _write(root, 'review.json', init_review(manifest, root))
    return {'manifest': 'manifest.json', 'worksheet': 'review.json', 'visualApproval': False,
            'temporalReview': 'UNREVIEWED', 'syntheticOnly': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', default='.', help='Project root; all other paths must stay within it')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo', help='Explicitly generate an original geometric example in --root')
    init = sub.add_parser('init', help='Create an UNREVIEWED worksheet; never overwrite an existing file')
    init.add_argument('manifest'); init.add_argument('worksheet')
    check = sub.add_parser('check', help='Check structure, freshness and optional recorded-row completeness')
    check.add_argument('manifest'); check.add_argument('worksheet')
    check.add_argument('--require-recorded', action='store_true')
    check.add_argument('--out', help='Optional new report path inside --root; existing files are not overwritten')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            report = demo(args.root)
        elif args.command == 'init':
            worksheet = init_review(_load(args.root, args.manifest), args.root)
            _write(args.root, args.worksheet, worksheet)
            report = {'worksheet': args.worksheet, 'rowCount': len(worksheet['rows']),
                      'visualApproval': False, 'temporalReview': 'UNREVIEWED'}
        else:
            report = check_review(_load(args.root, args.manifest), _load(args.root, args.worksheet),
                                  args.root, require_recorded=args.require_recorded)
            if args.out:
                _write(args.root, args.out, report)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if report.get('checkPassed', True) else 1
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'checkPassed': False, 'error': str(error),
                          'visualApproval': False, 'temporalReview': 'UNREVIEWED'}, indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
