"""Reproduce explicitly registered dash cels; no art generation or quality approval."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw, __version__ as PILLOW_VERSION

from dash_registration import align_body_axis, translate_shared_layer
from production_audit import audit_frames, audit_tracks
from repair_audit import gif_timing


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def confined(root, name):
    if not isinstance(name, str) or not name:
        raise ValueError('A project-relative asset path is required')
    relative = Path(name)
    result = (root / relative).resolve()
    if relative.is_absolute() or not result.is_relative_to(root):
        raise ValueError('Asset paths must stay inside the project directory')
    return result


def read_project(path, require_pins=True):
    path = Path(path).resolve()
    root = path.parent
    project = json.loads(path.read_text(encoding='utf-8'))
    if project.get('schema') != 'dash-registration-project/1':
        raise ValueError('Unknown dash project schema')
    canvas = project.get('canvas')
    if not isinstance(canvas, list) or len(canvas) != 2 or any(type(v) is not int or not 1 <= v <= 4096 for v in canvas):
        raise ValueError('Canvas must contain two positive integer dimensions <=4096')
    if project.get('view') not in ('front', 'side', 'back'):
        raise ValueError('Declare front, side or back; no missing view is inferred')
    rows = project.get('frames')
    if not isinstance(rows, list) or not 4 <= len(rows) <= 256:
        raise ValueError('Supply 4..256 actual authored frames')
    durations = project.get('durationsMs')
    if not isinstance(durations, list) or len(durations) != len(rows) or any(type(v) is not int or not 10 <= v <= 60000 or v % 10 for v in durations):
        raise ValueError('One positive GIF-compatible duration per actual cel is required')
    if sum(durations) > 655350:
        raise ValueError('Cycle duration exceeds the GIF single-hold maximum of 655350ms')
    small = project.get('smallHeight', 128)
    if type(small) is not int or not 1 <= small <= 4096:
        raise ValueError('smallHeight must be a positive integer <=4096')
    if not isinstance(project.get('sharedHead'), str):
        raise ValueError('sharedHead must be a project-relative PNG path')
    assets = {project['sharedHead']}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Every frame requires explicit registration')
        if not isinstance(row.get('body'), str):
            raise ValueError('Every frame needs a body PNG path')
        assets.add(row['body'])
        for key in ('sourceLandmarks', 'targetLandmarks'):
            points = np.asarray(row.get(key), dtype=float)
            if points.shape != (3, 2) or not np.isfinite(points).all():
                raise ValueError('Exactly three finite neck/chest/waist landmarks are required')
        if type(row.get('lockY')) is not int or not 0 < row['lockY'] <= canvas[1]:
            raise ValueError('lockY must be an integer row within the canvas')
        translation = row.get('headTranslation')
        if not isinstance(translation, list) or len(translation) != 2 or any(type(v) is not int for v in translation):
            raise ValueError('Shared head translation must be two integers')
    images, actual_pins = {}, {}
    for name in assets:
        source = confined(root, name)
        with Image.open(source) as image:
            if image.format != 'PNG' or image.mode != 'RGBA' or image.size != tuple(canvas):
                raise ValueError('Every input must be an RGBA PNG on the declared canvas')
            images[name] = image.copy()
        actual_pins[name] = digest(source)
    if require_pins and project.get('sourcePins') != actual_pins:
        raise ValueError('Source pins missing or stale; inspect changes before explicitly repinning')
    return path, project, images, actual_pins


def pin_project(path):
    path, project, _, pins = read_project(path, require_pins=False)
    project['sourcePins'] = pins
    path.write_text(json.dumps(project, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return pins


def render_frames(path):
    _, project, images, _ = read_project(path)
    head = images[project['sharedHead']]
    frames, bodies, heads = [], [], []
    for row in project['frames']:
        source = images[row['body']]
        body = align_body_axis(source, row['sourceLandmarks'], row['targetLandmarks'], row['lockY'])
        moved_head = translate_shared_layer(head, row['headTranslation'])
        frame = Image.alpha_composite(body, moved_head)
        if not np.array_equal(np.asarray(frame)[row['lockY']:], np.asarray(source)[row['lockY']:]):
            raise ValueError('Shared head would alter protected lower rows')
        bodies.append(body); heads.append(moved_head); frames.append(frame)
    return project, frames, bodies, heads


def axis_summary(points, durations_ms=None):
    values = np.asarray(points, dtype=float)
    adjacent = np.roll(values, -1, axis=0) - values
    half = len(values) // 2
    return {'xyRange': np.ptp(values, axis=0).tolist(),
            'maxAdjacentXYStepIncludingLoop': np.max(np.abs(adjacent), axis=0).tolist(),
            'lastToFirst': adjacent[-1].tolist(),
            'halfFrameCountOffsetMaxDifference': np.max(np.abs(values[:half] - values[half:]), axis=0).tolist() if len(values) % 2 == 0 else None,
            'halfCycleMaxDifference': np.max(np.abs(values[:half] - values[half:]), axis=0).tolist() if len(values) % 2 == 0 and durations_ms is not None and durations_ms[:half] == durations_ms[half:] else None,
            'halfCycleTimingMatched': bool(len(values) % 2 == 0 and durations_ms is not None and durations_ms[:half] == durations_ms[half:])}


def _preview(frames, height, durations, path):
    width = max(1, round(frames[0].width * height / frames[0].height))
    previews = []
    for frame in frames:
        canvas = Image.new('RGBA', (width, height), '#dce6e4')
        canvas.alpha_composite(frame.resize(canvas.size, Image.Resampling.LANCZOS))
        previews.append(canvas.convert('RGB'))
    previews[0].save(path, save_all=True, append_images=previews[1:], duration=durations,
                     loop=0, disposal=2, optimize=False)


def export_project(path, output):
    path = Path(path).resolve()
    project, frames, bodies, heads = render_frames(path)
    output = Path(output)
    if output.exists():
        raise ValueError('Use a new export directory; previous outputs are immutable')
    output.mkdir(parents=True)
    for i, (frame, body, head) in enumerate(zip(frames, bodies, heads)):
        frame.save(output / f'frame-{i:03d}.png')
        body.save(output / f'body-{i:03d}.png')
        head.save(output / f'head-{i:03d}.png')
    for label, height in [('native', frames[0].height), ('small', project.get('smallHeight', 128))]:
        _preview(frames, height, project['durationsMs'], output / f'preview-{label}.gif')
    cols = min(4, len(frames)); width, height = frames[0].size
    sheet = Image.new('RGBA', (width * cols, height * ((len(frames) + cols - 1) // cols)))
    for i, frame in enumerate(frames):
        sheet.alpha_composite(frame, (i % cols * width, i // cols * height))
    sheet.save(output / 'sheet.png')
    tracks = {'headTranslation': [row['headTranslation'] for row in project['frames']]}
    for j, landmark in enumerate(('neck', 'chest', 'waist')):
        # This project contract uses exactly the named three landmarks.
        tracks[landmark] = [row['targetLandmarks'][j] for row in project['frames']]
        tracks['source_' + landmark] = [row['sourceLandmarks'][j] for row in project['frames']]
    canvas_warnings = []
    with Image.open(confined(path.parent, project['sharedHead'])) as source_head:
        head_bounds = source_head.getchannel('A').getbbox()
    for i, (frame, row) in enumerate(zip(frames, project['frames'])):
        alpha = np.asarray(frame)[..., 3]
        border = np.zeros_like(alpha, dtype=bool); border[0, :] = border[-1, :] = True; border[:, 0] = border[:, -1] = True
        border_pixels = int(np.count_nonzero(alpha[border]))
        dx, dy = row['headTranslation']
        clipped_head = bool(head_bounds and (head_bounds[0]+dx < 0 or head_bounds[1]+dy < 0 or head_bounds[2]+dx > frame.width or head_bounds[3]+dy > frame.height))
        if border_pixels or clipped_head:
            canvas_warnings.append({'frame': i, 'visibleBorderPixels': border_pixels, 'sharedHeadWouldBeClipped': clipped_head})
    report = {
        'schema': 'dash-registration-export/1', 'view': project['view'],
        'projectSha256': digest(path), 'sourcePins': project['sourcePins'],
        'canvas': project['canvas'], 'authoredFrames': len(frames),
        'durationsMs': project['durationsMs'], 'periodMs': sum(project['durationsMs']),
        'frameAudit': audit_frames(sorted(output.glob('frame-*.png')), project['durationsMs']),
        'trackAudit': audit_tracks(tracks, project['durationsMs']),
        'axisSummary': {name: axis_summary(points, project['durationsMs']) for name, points in tracks.items()},
        'encodedGifTiming': {label: gif_timing(output / f'preview-{label}.gif') for label in ('native', 'small')},
        'canvasWarnings': canvas_warnings,
        'protectedLowerRowsExact': True, 'sharedHeadIntegerTranslation': True,
        'quality': 'draft', 'visualApproval': False, 'temporalReview': 'UNREVIEWED',
        'environment': {'Pillow': PILLOW_VERSION, 'NumPy': np.__version__},
        'limitations': ['Registration follows authored landmarks, not automatic anatomy detection.',
                       'Different cels can still vary in shape, arm depth, garment volume or support.',
                       'Preview exports and numeric checks are not observed normal-speed playback.',
                       'GIF encoders may coalesce identical consecutive cels; original PNGs retain every authored frame.'],
    }
    (output / 'export.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


def verify_export(path, output):
    output = Path(output)
    with tempfile.TemporaryDirectory() as directory:
        fresh = Path(directory) / 'rendered'
        export_project(path, fresh)
        expected = {p.name for p in fresh.iterdir() if p.is_file()}
        actual = {p.name for p in output.iterdir() if p.is_file()}
        mismatches = sorted(expected ^ actual)
        mismatches += sorted(name for name in expected & actual if (fresh / name).read_bytes() != (output / name).read_bytes())
    return {'byteExact': not mismatches, 'mismatches': mismatches, 'visualApproval': False}


def create_demo(output):
    """Original geometric source fixture, not imported character art or quality evidence."""
    output = Path(output)
    if output.exists():
        raise ValueError('Use a new demo directory')
    output.mkdir(parents=True)
    head = Image.new('RGBA', (128, 128)); d = ImageDraw.Draw(head)
    d.ellipse((55, 11, 73, 29), fill='#dca879'); d.rectangle((59, 17, 61, 19), fill='#213444')
    head.save(output / 'head.png')
    rows = []; bobs = [0, 2, 0, -2] * 2
    for i in range(8):
        jitter = [-2, 1, 0, 2, 2, -1, 1, -2][i]; vertical = [1, -1, 2, 0, -2, 1, 0, 2][i]
        body = Image.new('RGBA', head.size); d = ImageDraw.Draw(body)
        d.polygon([(52+jitter, 30+vertical), (76+jitter, 30+vertical), (79+jitter, 72+vertical), (49+jitter, 72+vertical)], fill='#3b8b85')
        d.line((51+jitter, 50+vertical, 77+jitter, 50+vertical), fill='#e9b745', width=3)
        step = int(round(7 * np.cos(2 * np.pi * i / 8)))
        d.line([(56, 70), (53-step, 92), (52-step, 116)], fill='#b85e66', width=10)
        d.line([(72, 70), (75+step, 92), (76+step, 116)], fill='#586da8', width=10)
        name = f'body-{i:03d}.png'; body.save(output / name)
        rows.append({'body': name, 'sourceLandmarks': [[64+jitter, y+vertical] for y in (30, 50, 70)],
                     'targetLandmarks': [[64, y+bobs[i]] for y in (30, 50, 70)],
                     'headTranslation': [0, bobs[i]], 'lockY': 90})
    project = {'schema': 'dash-registration-project/1', 'view': 'front', 'canvas': [128, 128],
               'sharedHead': 'head.png', 'frames': rows, 'durationsMs': [80, 90] * 4, 'smallHeight': 64,
               'fixtureOnly': True, 'provenance': 'Original code-drawn geometric shapes; MIT, not art-quality evidence.'}
    path = output / 'project.json'; path.write_text(json.dumps(project, indent=2) + '\n')
    pin_project(path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('pin'); p.add_argument('project')
    p = sub.add_parser('render'); p.add_argument('project'); p.add_argument('output')
    p = sub.add_parser('verify'); p.add_argument('project'); p.add_argument('output')
    p = sub.add_parser('demo'); p.add_argument('output')
    args = parser.parse_args()
    if args.command == 'pin':
        print(json.dumps({'sourcePins': pin_project(args.project)}, indent=2))
    elif args.command == 'render':
        result = export_project(args.project, args.output); print(json.dumps({'frames': result['authoredFrames'], 'quality': result['quality'], 'temporalReview': result['temporalReview']}))
    elif args.command == 'verify':
        result = verify_export(args.project, args.output); print(json.dumps(result)); return 0 if result['byteExact'] else 2
    else:
        path = create_demo(args.output); export_project(path, path.parent / 'rendered'); print(json.dumps({'project': str(path), 'quality': 'draft', 'temporalReview': 'UNREVIEWED'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
