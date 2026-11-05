"""Authored RGBA layers + explicit poses, without artwork inference.

Coordinates are canvas pixels with y pointing down. Layers are full-canvas RGBA
images, in back-to-front order. Chains must run downward in their REST pose;
destination chains may bend in any direction, but folded meshes are rejected.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image


def _points(value, name):
    array = np.asarray(value, dtype=float)
    if array.ndim != 2 or array.shape[1] != 2 or not np.isfinite(array).all():
        raise ValueError(f'{name} must contain finite [x, y] points')
    return array


def limb_phase(phase, owner, kind='leg'):
    """Physical left/right phases, independent of camera view.

    Same-side arm and leg are half a cycle apart. Viewer-left is NOT physical
    left in a front view. Use explicit ownership, never screen coordinates.
    """
    if owner not in ('left', 'right') or kind not in ('arm', 'leg'):
        raise ValueError('Expected left/right owner and arm/leg kind')
    if not math.isfinite(phase):
        raise ValueError('Phase must be finite')
    return (phase + (0.5 if owner == 'right' else 0) +
            (0.5 if kind == 'arm' else 0)) % 1.0


def project_forward(distance, view, depth_scale=0.25):
    """Project physical forward displacement to screen (x, y).

    Front/back use an authored depth proxy, not a 3-D reconstruction. Physical
    forward moves down-screen in front view and up-screen in back view.
    """
    if not math.isfinite(distance) or not math.isfinite(depth_scale) or depth_scale < 0:
        raise ValueError('Projection inputs must be finite; depth_scale nonnegative')
    axes = {'side_right': (1, 0), 'side_left': (-1, 0),
            'front': (0, depth_scale), 'back': (0, -depth_scale)}
    if view not in axes:
        raise ValueError('Unknown view')
    return np.asarray(axes[view], dtype=float) * distance


def support_height_offset(supports):
    """Fit body y from stance legs only, using explicit ankle targets.

    Each support has hip, ankle, lengths=[upper, lower], optional knee_flex
    (radians, 0 means straight) and weight. Swing legs must not be supplied.
    Returns the weighted least-squares vertical offset, or rejects impossible
    horizontal reach. This is a pose helper, not automatic foot locking.
    """
    offsets, weights = [], []
    for support in supports:
        hip, ankle = _points([support['hip'], support['ankle']], 'support joints')
        lengths = np.asarray(support['lengths'], dtype=float)
        flex = float(support.get('knee_flex', 0))
        weight = float(support.get('weight', 1))
        if (lengths.shape != (2,) or not np.isfinite(lengths).all() or
                np.any(lengths <= 0) or not 0 <= flex < math.pi or
                not math.isfinite(weight) or weight <= 0):
            raise ValueError('Invalid support lengths, flex or weight')
        reach2 = float(np.sum(lengths ** 2) + 2 * np.prod(lengths) * math.cos(flex))
        vertical2 = reach2 - (ankle[0] - hip[0]) ** 2
        if vertical2 < -1e-9:
            raise ValueError('Support target exceeds horizontal reach')
        offsets.append(ankle[1] - math.sqrt(max(0, vertical2)) - hip[1])
        weights.append(weight)
    if not offsets:
        raise ValueError('At least one stance support is required')
    return float(np.average(offsets, weights=weights))


@dataclass(frozen=True)
class PeriodicSupportFit:
    """Periodic body-y approximation, plus measured constraint diagnostics.

    Calling the result evaluates a scalar phase. Coefficients are ordered
    constant, cos(1), sin(1), cos(2), sin(2), ... . A smooth fit does not imply
    exact foot contact, feasible limb reach between samples, or natural gait.
    """
    coefficients: tuple
    diagnostics: dict

    def __call__(self, phase):
        if not math.isfinite(phase):
            raise ValueError('Phase must be finite')
        return float(_fourier_basis([phase], (len(self.coefficients) - 1) // 2)[0]
                     @ np.asarray(self.coefficients))


def _fourier_basis(phases, harmonics):
    phase = np.asarray(phases, dtype=float) % 1.0
    columns = [np.ones_like(phase)]
    for frequency in range(1, harmonics + 1):
        angle = 2 * math.pi * frequency * phase
        columns.extend((np.cos(angle), np.sin(angle)))
    return np.column_stack(columns)


def fit_periodic_support_height(samples, harmonics=2):
    """Fit a smooth, periodic body-y curve to authored stance constraints.

    samples = [{'phase': fraction, 'supports': [support, ...]}, ...]. Each
    support uses the same fields as support_height_offset. Multiple supports
    at exchange remain separate weighted observations; swing constraints must
    not be supplied (an explicit stance=False is rejected). Phases wrap modulo
    one, so 0 and 1 describe the same instant, not separate time positions.

    Returns PeriodicSupportFit, callable at any phase. Diagnostics include
    weighted RMS/max vertical residuals, input horizontal-reach margins and
    fitted straight-leg reach margins at supplied samples. Negative fitted
    reach margins flag overextension. Positive margins do NOT certify contact,
    shape quality, or unsampled reach. Rank-deficient or horizontally impossible
    input raises ValueError. No fitting is enabled automatically by rendering.
    """
    if type(harmonics) is not int or harmonics < 0:
        raise ValueError('harmonics must be a nonnegative integer')
    observations = []
    for sample_index, sample in enumerate(samples):
        phase = float(sample['phase'])
        if not math.isfinite(phase):
            raise ValueError('Sample phase must be finite')
        supports = sample['supports']
        if not supports:
            raise ValueError('Each sample requires at least one stance support')
        for support_index, support in enumerate(supports):
            if support.get('stance', True) is not True:
                raise ValueError('Only explicitly supplied stance supports may be fitted')
            target = support_height_offset([support])
            hip, ankle = _points([support['hip'], support['ankle']], 'support joints')
            lengths = np.asarray(support['lengths'], dtype=float)
            flex = float(support.get('knee_flex', 0))
            effective_reach = math.sqrt(float(np.sum(lengths ** 2) +
                                       2 * np.prod(lengths) * math.cos(flex)))
            observations.append({'sample': sample_index, 'support': support_index,
                                 'phase': phase % 1, 'target': target,
                                 'weight': float(support.get('weight', 1)),
                                 'hip': hip, 'ankle': ankle,
                                 'reach': effective_reach, 'max_reach': float(sum(lengths))})
    terms = 2 * harmonics + 1
    if len(observations) < terms:
        raise ValueError('Too few support observations for the requested harmonics')
    basis = _fourier_basis([row['phase'] for row in observations], harmonics)
    targets = np.asarray([row['target'] for row in observations])
    weights = np.asarray([row['weight'] for row in observations])
    # Rescaling preserves weighted least squares and avoids overflow from sqrt.
    normalized_weights = weights / weights.max()
    root_weights = np.sqrt(normalized_weights)
    coefficients, _, rank, singular = np.linalg.lstsq(
        basis * root_weights[:, None], targets * root_weights, rcond=None)
    if rank != terms:
        raise ValueError('Support phases do not determine the requested Fourier fit')
    predicted = basis @ coefficients
    residuals = predicted - targets
    details = []
    for row, prediction, residual in zip(observations, predicted, residuals):
        fitted_delta = row['ankle'] - row['hip'] - [0, prediction]
        distance = float(np.linalg.norm(fitted_delta))
        details.append({'sample': row['sample'], 'support': row['support'],
                        'phase': row['phase'], 'target_offset': row['target'],
                        'fitted_offset': float(prediction), 'vertical_residual': float(residual),
                        'horizontal_reach_margin': row['reach'] - abs(float(fitted_delta[0])),
                        'straight_leg_reach_margin': row['max_reach'] - distance,
                        'effective_reach_error': distance - row['reach'],
                        'ankle_below_hip': bool(fitted_delta[1] >= 0)})
    diagnostics = {
        'observation_count': len(details), 'harmonics': harmonics, 'rank': int(rank),
        'condition_number': float(singular[0] / singular[-1]),
        'weighted_rms_vertical_residual': float(np.sqrt(np.average(residuals ** 2, weights=normalized_weights))),
        'max_abs_vertical_residual': float(np.max(np.abs(residuals))),
        'minimum_horizontal_reach_margin': min(row['horizontal_reach_margin'] for row in details),
        'minimum_fitted_straight_leg_reach_margin': min(row['straight_leg_reach_margin'] for row in details),
        'constraints': details,
        'scope': 'Supplied stance samples only; no exact-contact or unsampled-reach guarantee.'}
    return PeriodicSupportFit(tuple(float(value) for value in coefficients), diagnostics)


def chain_mapper(rest, posed, root_blend=0, root_translation=None):
    """Piecewise centerline deformation with optional bounded root blend.

    The rest chain is strictly increasing in y. Width offsets remain horizontal
    (a 2-D strip warp). Within root_blend pixels below the root, smoothstep mixes
    body-owned translation and chain motion; above the root only the body moves.
    Below that bounded band, the limb owns all motion. Author hidden overlap;
    this function cannot paint an absent shoulder or unseen limb.
    """
    rest, posed = _points(rest, 'rest'), _points(posed, 'posed')
    if len(rest) < 2 or posed.shape != rest.shape or np.any(np.diff(rest[:, 1]) <= 0):
        raise ValueError('Matching chains with at least two downward rest joints required')
    if not math.isfinite(root_blend) or root_blend < 0:
        raise ValueError('root_blend must be finite and nonnegative')
    translation = posed[0] - rest[0] if root_translation is None else np.asarray(root_translation, dtype=float)
    if translation.shape != (2,) or not np.isfinite(translation).all():
        raise ValueError('root_translation must be a finite [x, y] vector')

    def mapper(point):
        point = np.asarray(point, dtype=float)
        segment = int(np.clip(np.searchsorted(rest[:, 1], point[1], side='right') - 1, 0, len(rest) - 2))
        t = (point[1] - rest[segment, 1]) / (rest[segment + 1, 1] - rest[segment, 1])
        center = rest[segment] + t * (rest[segment + 1] - rest[segment])
        target = posed[segment] + t * (posed[segment + 1] - posed[segment])
        mapped = target + [point[0] - center[0], 0]
        if root_blend:
            w = float(np.clip((point[1] - rest[0, 1]) / root_blend, 0, 1))
            w = w * w * (3 - 2 * w)
            mapped = (1 - w) * (point + translation) + w * mapped
        return mapped
    return mapper


def warp_layer(source, mapper, step=8):
    """Forward triangular mesh, bilinear premultiplied-alpha sampling.

    Output has the input dimensions. Out-of-canvas motion is clipped. Inverted
    or collapsed triangles raise an error instead of silently rendering folds.
    Smaller step improves curved-band approximation at increased runtime.
    """
    if not isinstance(step, int) or isinstance(step, bool) or step < 1:
        raise ValueError('step must be a positive integer')
    source = source.convert('RGBA')
    width, height = source.size
    box = source.getchannel('A').getbbox()
    if box is None:
        return source.copy()
    pixels = np.asarray(source, dtype=float) / 255
    pixels[:, :, :3] *= pixels[:, :, 3:4]
    output = np.zeros_like(pixels)
    x0, y0, x1, y1 = box
    xs, ys = list(range(x0, x1, step)) + [x1], list(range(y0, y1, step)) + [y1]
    vertices = {(x, y): np.asarray(mapper(np.array([x, y], dtype=float))) for y in ys for x in xs}
    for row in range(len(ys) - 1):
        for col in range(len(xs) - 1):
            corners = [(xs[col], ys[row]), (xs[col + 1], ys[row]),
                       (xs[col + 1], ys[row + 1]), (xs[col], ys[row + 1])]
            for indices in ((0, 1, 2), (0, 2, 3)):
                src = np.asarray([corners[i] for i in indices], dtype=float)
                dst = np.asarray([vertices[corners[i]] for i in indices], dtype=float)
                if dst.shape != (3, 2) or not np.isfinite(dst).all():
                    raise ValueError('Mapper returned invalid coordinates')
                matrix = np.column_stack((dst[1] - dst[0], dst[2] - dst[0]))
                if np.linalg.det(matrix) <= 1e-9:
                    raise ValueError('Deformation contains a folded or collapsed triangle')
                lo = np.maximum(np.floor(dst.min(axis=0)), [0, 0]).astype(int)
                hi = np.minimum(np.ceil(dst.max(axis=0)), [width, height]).astype(int)
                if np.any(hi <= lo):
                    continue
                yy, xx = np.mgrid[lo[1]:hi[1], lo[0]:hi[0]]
                uv = (np.stack((xx + .5, yy + .5), axis=-1) - dst[0]) @ np.linalg.inv(matrix).T
                inside = (uv >= -1e-9).all(axis=-1) & (uv.sum(axis=-1) <= 1 + 1e-9)
                xy = src[0] + uv @ np.stack((src[1] - src[0], src[2] - src[0])) - .5
                base = np.floor(xy).astype(int)
                fraction = xy - base
                sample = np.zeros((*xx.shape, 4))
                for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    sx, sy = base[..., 0] + dx, base[..., 1] + dy
                    weight = (fraction[..., 0] if dx else 1 - fraction[..., 0]) * (fraction[..., 1] if dy else 1 - fraction[..., 1])
                    valid = (sx >= 0) & (sx < width) & (sy >= 0) & (sy < height)
                    sample += pixels[np.clip(sy, 0, height - 1), np.clip(sx, 0, width - 1)] * (weight * valid)[..., None]
                tile = output[lo[1]:hi[1], lo[0]:hi[0]]
                tile[inside] = sample[inside]
    alpha = output[..., 3:4]
    output[..., :3] = np.divide(output[..., :3], alpha, out=np.zeros_like(output[..., :3]), where=alpha > 0)
    return Image.fromarray(np.rint(np.clip(output * 255, 0, 255)).astype('uint8'), 'RGBA')


def load_manifest(path):
    """Load version 1 JSON and local assets. Paths cannot escape its directory."""
    path = Path(path)
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('version') != 1:
        raise ValueError('Expected manifest version 1')
    size = manifest.get('canvas')
    if not isinstance(size, list) or len(size) != 2 or any(type(v) is not int or v <= 0 for v in size):
        raise ValueError('canvas must be [positive width, positive height]')
    layers = manifest.get('layers')
    if not isinstance(layers, list) or not layers:
        raise ValueError('At least one layer is required')
    root, assets = path.resolve().parent, {}
    for layer in layers:
        name = layer['name']
        if not isinstance(name, str) or not name or name in assets:
            raise ValueError('Layer names must be nonempty and unique')
        relative = Path(layer['file'])
        asset_path = (root / relative).resolve()
        if relative.is_absolute() or not asset_path.is_relative_to(root):
            raise ValueError('Layer paths must stay inside the manifest directory')
        with Image.open(asset_path) as image:
            if image.mode != 'RGBA' or image.size != tuple(size):
                raise ValueError('Layers must be full-canvas RGBA images')
            assets[name] = image.copy()
        if 'rest' in layer:
            chain_mapper(layer['rest'], layer['rest'], layer.get('root_blend', 0))
    if not isinstance(manifest.get('frames'), list) or not manifest['frames']:
        raise ValueError('At least one explicit frame is required')
    return manifest, assets


def render_frame(manifest, assets, frame_index):
    """Render explicit frame poses and optional layer order; never infer phase."""
    frame = manifest['frames'][frame_index]
    layers = {layer['name']: layer for layer in manifest['layers']}
    order = frame.get('order', list(layers))
    if len(order) != len(layers) or set(order) != set(layers):
        raise ValueError('Frame order must list every layer exactly once')
    poses = frame.get('poses', {})
    if set(poses) - set(layers):
        raise ValueError('Pose refers to an unknown layer')
    translation = np.asarray(frame.get('translation', [0, 0]), dtype=float)
    if translation.shape != (2,) or not np.isfinite(translation).all():
        raise ValueError('Frame translation must be finite [x, y]')
    result = Image.new('RGBA', tuple(manifest['canvas']))
    for name in order:
        layer = layers[name]
        if 'rest' in layer:
            posed = np.asarray(poses.get(name, layer['rest']), dtype=float) + translation
            mapper = chain_mapper(layer['rest'], posed, layer.get('root_blend', 0), translation)
        else:
            if name in poses:
                raise ValueError('A posed layer requires a rest chain')
            mapper = lambda point: point + translation
        result.alpha_composite(warp_layer(assets[name], mapper, manifest.get('mesh_step', 8)))
    return result


def _prepare_output(output):
    """Refuse to overwrite any existing artifact, including unrelated files."""
    output = Path(output)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Output must be a new or empty directory')
    output.mkdir(parents=True, exist_ok=True)
    return output


def write_demo(output, frame_count=12):
    """Write original geometric fixtures and explicit [0, 1) pose loops.

    These deliberately simple colored shapes demonstrate ownership and phase;
    they are not a natural-walk benchmark or source artwork reconstruction.
    """
    from PIL import ImageDraw
    if type(frame_count) is not int or frame_count < 4:
        raise ValueError('At least four frames required')
    output = _prepare_output(output)
    for view in ('front', 'side_right', 'back'):
        root = output / view
        root.mkdir(parents=True, exist_ok=True)
        layers = []
        rests = {}
        for owner, lateral, color in [('left', -1, '#e38a39'), ('right', 1, '#437ec4')]:
            if view == 'front':
                lateral *= -1
            for kind in ('leg', 'arm'):
                x = 48 + lateral * (9 if kind == 'leg' else 17)
                if view == 'side_right':
                    x = 48 + lateral * 3
                y, length = (51, 32) if kind == 'leg' else (29, 26)
                rest = [[x, y], [x, y + length / 2], [x, y + length]]
                name = owner + '_' + kind
                rests[name] = rest
                image = Image.new('RGBA', (96, 96))
                draw = ImageDraw.Draw(image)
                draw.line([tuple(point) for point in rest], fill=color, width=8)
                draw.ellipse((x - 4, y + length - 3, x + 4, y + length + 3), fill=color)
                image.save(root / (name + '.png'))
                layers.append({'name': name, 'file': name + '.png', 'owner': owner,
                               'rest': rest, 'root_blend': 7 if kind == 'arm' else 0})
        body = Image.new('RGBA', (96, 96))
        draw = ImageDraw.Draw(body)
        draw.rounded_rectangle((32, 25, 64, 56), radius=6, fill='#54646c')
        draw.ellipse((37, 7, 59, 29), fill='#bdad91')
        body.save(root / 'body.png')
        layers.append({'name': 'body', 'file': 'body.png'})
        frames = []
        for i in range(frame_count):
            phase = i / frame_count
            poses = {}
            for name, rest in rests.items():
                owner, kind = name.split('_')
                q = limb_phase(phase, owner, kind)
                forward = 7 * math.cos(2 * math.pi * q)
                shift = project_forward(forward, view, depth_scale=.35)
                posed = np.asarray(rest, dtype=float).copy()
                posed[1] += shift * .45
                posed[2] += shift
                if kind == 'leg':
                    posed[1:, 1] -= max(0, math.sin(2 * math.pi * q)) * np.array([1.5, 3])
                poses[name] = posed.tolist()
            frames.append({'phase': phase, 'poses': poses,
                           'order': ['left_arm', 'left_leg', 'right_leg', 'body', 'right_arm']})
        manifest = {'version': 1, 'canvas': [96, 96], 'mesh_step': 4,
                    'view': view, 'layers': layers, 'frames': frames}
        path = root / 'manifest.json'
        path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        manifest, assets = load_manifest(path)
        rendered = [render_frame(manifest, assets, i) for i in range(frame_count)]
        for i, image in enumerate(rendered):
            image.save(root / f'frame-{i:04d}.png')
        previews = []
        for image in rendered:
            background = Image.new('RGBA', image.size, '#e8e4db')
            background.alpha_composite(image)
            previews.append(background.convert('RGB'))
        previews[0].save(root / 'preview.gif', save_all=True, append_images=previews[1:],
                         duration=80, loop=0, disposal=2)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path, nargs='?')
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--demo', type=Path, metavar='OUT', help='Generate three geometric demo views')
    args = parser.parse_args(argv)
    if args.demo:
        if args.manifest or args.output:
            parser.error('--demo cannot be combined with manifest/output')
        write_demo(args.demo)
        return 0
    if args.manifest is None or args.output is None:
        parser.error('manifest and output are required unless --demo is used')
    manifest, assets = load_manifest(args.manifest)
    _prepare_output(args.output)
    for i in range(len(manifest['frames'])):
        render_frame(manifest, assets, i).save(args.output / f'frame-{i:04d}.png')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
