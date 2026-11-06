"""Authored dash-registration and local arm-repair primitives.

Requires only the project's NumPy/Pillow dependencies. No source-art discovery,
segmentation, automatic anatomy, or visual-quality certification is performed.
Coordinates use image edges, with x rightward and y downward. Image operations
require RGBA input, return new images, and keep the source unchanged.

The shape-preserving Hermite interpolator uses weighted harmonic-mean interior
slopes and limited one-sided endpoints (PCHIP), implemented here without SciPy.
Image warps use one-row Pillow meshes: their rasterization approximates the
continuous map; declared protected rows are restored byte for byte afterward.

Run ``python dash_registration.py --demo NEW_DIRECTORY`` for an original,
code-native geometric fixture, reproducible recipe, before/after PNGs, GIFs and
checksums. These are algorithm demonstrations, not character or gait approvals.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from numbers import Integral
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, __version__ as PILLOW_VERSION


def _finite(value, name):
    try:
        arr = np.array(value, dtype=float, copy=True)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'{name} must contain finite numbers') from exc
    if not np.isfinite(arr).all():
        raise ValueError(f'{name} must contain finite numbers')
    return arr


def _number(value, name, *, positive=False):
    arr = _finite(value, name)
    if arr.ndim or isinstance(value, (bool, np.bool_)):
        raise ValueError(f'{name} must be a finite number')
    result = float(arr)
    if positive and result <= 0:
        raise ValueError(f'{name} must be positive')
    return result


def _integer(value, name, *, minimum=None):
    if not isinstance(value, Integral) or isinstance(value, (bool, np.bool_)):
        raise ValueError(f'{name} must be an integer')
    result = int(value)
    if minimum is not None and result < minimum:
        raise ValueError(f'{name} must be >= {minimum}')
    return result


def _points(value, name):
    arr = _finite(value, name)
    if arr.ndim < 1 or arr.shape[-1] != 2:
        raise ValueError(f'{name} must have shape (..., 2)')
    return arr


def _rgba(image):
    if not isinstance(image, Image.Image) or image.mode != 'RGBA':
        raise ValueError('image must be a Pillow RGBA image')
    return image


def _resampling(value):
    allowed = (Image.Resampling.NEAREST, Image.Resampling.BILINEAR,
               Image.Resampling.BICUBIC)
    if isinstance(value, bool) or value not in allowed:
        raise ValueError('mesh resampling must be NEAREST, BILINEAR or BICUBIC')
    return value


class ShapePreservingCubic:
    """One-dimensional PCHIP with explicit in-range queries only.

    x must strictly increase; y can be monotone or non-monotone. Each interval
    stays between its endpoint values, including at sign-changing extrema.
    Inputs are copied. There is deliberately no silent extrapolation.
    """
    def __init__(self, x, y):
        x, y = _finite(x, 'x'), _finite(y, 'y')
        if x.ndim != 1 or y.shape != x.shape or len(x) < 2:
            raise ValueError('x and y must be matching vectors of length >= 2')
        h = np.diff(x)
        if np.any(h <= 0):
            raise ValueError('x must be strictly increasing')
        slope = np.diff(y) / h
        d = np.zeros_like(x)
        if len(x) == 2:
            d[:] = slope[0]
        else:
            for k in range(1, len(x)-1):
                left, right = slope[k-1], slope[k]
                if left != 0 and right != 0 and np.sign(left) == np.sign(right):
                    w1, w2 = 2*h[k]+h[k-1], h[k]+2*h[k-1]
                    d[k] = (w1+w2)/(w1/left+w2/right)
            def endpoint(h0, h1, m0, m1):
                value = ((2*h0+h1)*m0-h0*m1)/(h0+h1)
                if np.sign(value) != np.sign(m0):
                    return 0.0
                if np.sign(m0) != np.sign(m1) and abs(value) > abs(3*m0):
                    return 3*m0
                return value
            d[0] = endpoint(h[0], h[1], slope[0], slope[1])
            d[-1] = endpoint(h[-1], h[-2], slope[-1], slope[-2])
        self._x, self._y, self._d = x, y, d
        for array in (self._x, self._y, self._d):
            array.flags.writeable = False

    def __call__(self, query):
        q = _finite(query, 'query')
        if np.any(q < self._x[0]) or np.any(q > self._x[-1]):
            raise ValueError('query lies outside interpolation range')
        k = np.clip(np.searchsorted(self._x, q, side='right')-1,
                    0, len(self._x)-2)
        h = self._x[k+1]-self._x[k]
        t = (q-self._x[k])/h
        result = ((2*t**3-3*t**2+1)*self._y[k]
                  +(t**3-2*t**2+t)*h*self._d[k]
                  +(-2*t**3+3*t**2)*self._y[k+1]
                  +(t**3-t**2)*h*self._d[k+1])
        return float(result) if q.ndim == 0 else result


def _axis_landmarks(source_landmarks, target_landmarks, lock_y):
    source = _points(source_landmarks, 'source_landmarks')
    target = _points(target_landmarks, 'target_landmarks')
    lock_y = _integer(lock_y, 'lock_y', minimum=1)
    if source.ndim != 2 or len(source) < 2 or target.shape != source.shape:
        raise ValueError('landmarks must be matching N by 2 arrays, N >= 2')
    for name, points in [('source', source), ('target', target)]:
        if np.any(np.diff(points[:, 1]) <= 0):
            raise ValueError(f'{name} landmark rows must be strictly increasing')
        if points[0, 1] < 0 or points[-1, 1] >= lock_y:
            raise ValueError(f'{name} landmark rows must lie in [0, lock_y)')
    if not np.all(target[:, 0] == target[0, 0]):
        raise ValueError('target landmarks must share one authored axis x')
    return source, target, lock_y


def axis_inverse_mapping(source_landmarks, target_landmarks, lock_y):
    """Return destination-to-source registration of ordered torso landmarks.

    Usually landmarks are neck, chest and waist. Their y coordinates must be
    strictly increasing in both arrays. Target x is a single authored axis.
    Above the first target row the map is a translation. At/below lock_y it is
    identity. An identity anchor at lock_y joins the protected lower region.
    """
    source, target, lock_y = _axis_landmarks(source_landmarks, target_landmarks, lock_y)
    axis = target[0, 0]
    inv_y = ShapePreservingCubic(np.r_[target[:, 1], lock_y],
                                np.r_[source[:, 1], lock_y])
    source_axis = ShapePreservingCubic(np.r_[source[:, 1], lock_y],
                                      np.r_[source[:, 0], axis])
    identity = np.array_equal(source, target)
    def inverse(points):
        p = _points(points, 'points')
        if identity:
            return p
        original_shape = p.shape
        p = p.reshape(-1, 2)
        out = p.copy()
        top = p[:, 1] <= target[0, 1]
        middle = (p[:, 1] > target[0, 1]) & (p[:, 1] < lock_y)
        out[top] += source[0]-target[0]
        out[middle, 1] = inv_y(p[middle, 1])
        out[middle, 0] += source_axis(out[middle, 1])-axis
        return out.reshape(original_shape)
    return inverse


def _mesh_warp(image, inverse, resampling):
    width, height = image.size
    mesh = []
    for y in range(height):
        corners = np.array([[0, y], [0, y+1], [width, y+1], [width, y]], float)
        mapped = inverse(corners)
        mesh.append(((0, y, width, y+1), tuple(mapped.ravel())))
    return image.transform(image.size, Image.Transform.MESH, mesh,
                           resample=_resampling(resampling), fillcolor=(0, 0, 0, 0))


def align_body_axis(body, source_landmarks, target_landmarks, lock_y, *,
                    resampling=Image.Resampling.BICUBIC):
    """Return registered RGBA body, preserving every row y >= lock_y exactly.

    Landmarks are explicitly authored, never inferred from the silhouette.
    The output canvas equals the input canvas; off-canvas content is clipped.
    Protected pixels include transparent-pixel RGB, not merely visible alpha.
    """
    _rgba(body)
    source, target, lock_y = _axis_landmarks(source_landmarks, target_landmarks, lock_y)
    _resampling(resampling)
    if lock_y > body.height:
        raise ValueError('lock_y must not exceed image height')
    if np.any(source[:, 0] < 0) or np.any(source[:, 0] > body.width) or not 0 <= target[0, 0] <= body.width:
        raise ValueError('landmark x coordinates must lie within canvas edges')
    if np.array_equal(source, target):
        return body.copy()
    out = _mesh_warp(body, axis_inverse_mapping(source, target, lock_y), resampling)
    out.paste(body.crop((0, lock_y, body.width, body.height)), (0, lock_y))
    return out


def translate_shared_layer(layer, translation):
    """Translate immutable artwork by integer pixels, without resampling.

    The same-size transparent canvas clips at its edges. All copied RGBA bytes
    are preserved, even translucent and fully transparent pixels. Non-integer
    values (including 2.0) are rejected to prevent accidental subpixel filtering.
    """
    _rgba(layer)
    try:
        dx, dy = translation
    except (TypeError, ValueError) as exc:
        raise ValueError('translation must contain two integers') from exc
    dx, dy = _integer(dx, 'dx'), _integer(dy, 'dy')
    out = Image.new('RGBA', layer.size)
    out.paste(layer, (dx, dy))  # No mask: alpha is data, not a blending weight.
    return out


def shaft_hand_mapping(start, wrist, *, length_scale=1.0, width_scale=1.0,
                       target_start=None, rotation_radians=0.0):
    """Return a forward map extending a shaft while keeping its hand rigid.

    The source shaft runs from start to wrist. Beyond the wrist plane, points
    receive only a rigid rotation/translation. Shaft width changes fade to 1
    at both endpoints. Before start, points also move rigidly. target_start
    anchors the root, optionally after a parent's transform. For a two-bone
    arm, map the upper segment first, then use its endpoint as the forearm root.

    This is a geometric map, not a rasterizer or automatic hand segmentation.
    Authored hand pixels must be beyond the wrist plane, or belong to their own
    rigid hand layer. A bent joint still needs source-specific layer ownership.
    """
    start, wrist = _points(start, 'start'), _points(wrist, 'wrist')
    if start.shape != (2,) or wrist.shape != (2,):
        raise ValueError('start and wrist must be points')
    target = start.copy() if target_start is None else _points(target_start, 'target_start')
    if target.shape != (2,):
        raise ValueError('target_start must be a point')
    length_scale = _number(length_scale, 'length_scale', positive=True)
    width_scale = _number(width_scale, 'width_scale', positive=True)
    angle = _number(rotation_radians, 'rotation_radians')
    length = float(np.linalg.norm(wrist-start))
    if length <= 0:
        raise ValueError('start and wrist must differ')
    axis = (wrist-start)/length
    normal = np.array([-axis[1], axis[0]])
    c, s = math.cos(angle), math.sin(angle)
    rotation = np.array([[c, -s], [s, c]])
    identity = length_scale == width_scale == 1 and angle == 0 and np.array_equal(start, target)
    def forward(points):
        p = _points(points, 'points')
        if identity:
            return p
        relative = p-start
        along, across = relative@axis, relative@normal
        t = np.clip(along/length, 0, 1)
        extended = along+(length_scale-1)*np.clip(along, 0, length)
        # Exact 1 at the hand boundary, rather than floating-point sin(pi).
        taper = 16*t*t*(1-t)*(1-t)
        thickness = 1+(width_scale-1)*taper
        local = extended[..., None]*axis+(across*thickness)[..., None]*normal
        return target+local@rotation.T
    return forward


def _width_settings(centerline_x, root_y, blend_end_y, width_scale):
    centers = _finite(centerline_x, 'centerline_x')
    if centers.ndim != 1 or len(centers) < 2:
        raise ValueError('centerline_x must contain one center per row, at least two')
    root = _number(root_y, 'root_y')
    end = _number(blend_end_y, 'blend_end_y')
    scale = _number(width_scale, 'width_scale', positive=True)
    if not 0 <= root < end <= len(centers)-1:
        raise ValueError('require 0 <= root_y < blend_end_y <= last row')
    return centers, root, end, scale


def _width_components(points, centers, root, end, scale):
    y = points[..., 1]
    center = np.interp(y, np.arange(len(centers)), centers)
    t = np.clip((y-root)/(end-root), 0, 1)
    width = 1+(scale-1)*t*t*(3-2*t)
    return center, width


def row_width_mapping(centerline_x, *, root_y, blend_end_y, width_scale=1.0):
    """Return a forward width-only map around an authored per-row centerline.

    Each centerline point stays fixed. Every point at/above root_y is fixed;
    width smoothly reaches width_scale at blend_end_y. This does not lengthen
    the shoulder-to-hand path or infer centers from skin color/alpha.
    """
    settings = _width_settings(centerline_x, root_y, blend_end_y, width_scale)
    def forward(points):
        p = _points(points, 'points')
        center, width = _width_components(p, *settings)
        p[..., 0] = center+(p[..., 0]-center)*width
        return p
    return forward


def widen_rows(image, centerline_x, *, root_y, blend_end_y, width_scale=1.0,
               resampling=Image.Resampling.BICUBIC):
    """Warp an isolated arm layer horizontally; copy locked root rows exactly."""
    _rgba(image)
    settings = _width_settings(centerline_x, root_y, blend_end_y, width_scale)
    _resampling(resampling)
    centers, root, end, scale = settings
    if len(centers) != image.height:
        raise ValueError('centerline_x must contain one value per image row')
    if scale == 1:
        return image.copy()
    def inverse(points):
        p = _points(points, 'points')
        center, width = _width_components(p, *settings)
        p[..., 0] = center+(p[..., 0]-center)/width
        return p
    out = _mesh_warp(image, inverse, resampling)
    locked_end = int(math.floor(root))+1
    out.paste(image.crop((0, 0, image.width, locked_end)), (0, 0))
    return out


def cycle_schedule(durations_ms):
    """Explicit half-open frame intervals, suitable for a GIF without drift.

    GIF timing is in 10 ms ticks. Reject finer durations rather than silently
    rounding them. There is no duplicated phase-1 endpoint. Phases are elapsed
    time / full duration, not frame index / frame count for unequal holds.
    """
    try:
        durations = list(durations_ms)
    except TypeError as exc:
        raise ValueError('durations_ms must be a non-empty sequence') from exc
    if not durations:
        raise ValueError('durations_ms must be a non-empty sequence')
    durations = [_integer(d, 'duration', minimum=10) for d in durations]
    if any(d % 10 for d in durations):
        raise ValueError('GIF durations must be exact multiples of 10 ms')
    total, start = sum(durations), 0
    frames = []
    for i, duration in enumerate(durations):
        frames.append({'frame': i, 'startMs': start, 'endMs': start+duration,
                       'durationMs': duration, 'phase': start/total})
        start += duration
    return {'durationMs': total, 'frames': frames,
            'endpointPolicy': 'half-open intervals; phase 1 wraps to phase 0'}


def cycle_frame_at(durations_ms, time_ms):
    """Index the exact held frame at time_ms; negative time wraps too."""
    schedule = cycle_schedule(durations_ms)
    time_ms = _number(time_ms, 'time_ms')
    phase_ms = time_ms % schedule['durationMs']
    return bisect.bisect_right([f['endMs'] for f in schedule['frames']], phase_ms)


def _flatten(image):
    bg = Image.new('RGBA', image.size, (238, 242, 246, 255))
    bg.alpha_composite(image)
    return bg.convert('RGB')


def build_demo(output):
    """Write original geometric fixtures. Refuse to overwrite any directory."""
    out = Path(output)
    if out.exists():
        raise ValueError('demo output must be a new directory')
    out.mkdir(parents=True)
    width, height, lock = 192, 224, 148
    durations = [70, 90, 80, 110, 70, 90, 80, 110]
    timeline = cycle_schedule(durations)
    head = Image.new('RGBA', (width, height))
    hd = ImageDraw.Draw(head)
    hd.rounded_rectangle((79, 16, 113, 48), radius=6, fill='#e5b866', outline='#22354a', width=2)
    hd.rectangle((85, 28, 90, 33), fill='#22354a')
    hd.rectangle((102, 28, 107, 33), fill='#22354a')
    head.save(out/'shared-head.png')
    before, after, recipes = [], [], []
    for item in timeline['frames']:
        i, phase = item['frame'], item['phase']
        angle = phase*2*math.pi
        drift = [round(5*math.sin(angle)), round(8*math.cos(angle)), round(4*math.sin(angle+1))]
        bob = round(2*math.sin(angle*2))
        source = [[96+drift[0], 55+round(2*math.cos(angle))],
                  [96+drift[1], 88+round(3*math.sin(angle))],
                  [96+drift[2], 125+round(2*math.cos(angle+1))]]
        target = [[96, 55+bob], [96, 88+bob], [96, 125+bob]]
        body = Image.new('RGBA', (width, height))
        draw = ImageDraw.Draw(body)
        draw.polygon([(x-22, y) for x, y in source]+[(x+22, y) for x, y in source[::-1]], fill='#2c95a0', outline='#22354a')
        draw.polygon([(source[-1][0]-22, source[-1][1]), (source[-1][0]+22, source[-1][1]), (120, lock+2), (72, lock+2)], fill='#2c95a0')
        for x, y in source:
            draw.rectangle((x-4, y-2, x+4, y+2), fill='#f2d16b')
        # Distinct code-native lower poses; these rows must be exactly restored.
        stride = round(9*math.cos(angle))
        draw.line((82, lock, 82+stride, height-18), fill='#485d9d', width=13)
        draw.line((110, lock, 110-stride, height-18), fill='#9561a4', width=13)
        draw.rectangle((72+stride, height-21, 90+stride, height-14), fill='#22354a')
        draw.rectangle((102-stride, height-21, 120-stride, height-14), fill='#22354a')
        repaired = align_body_axis(body, source, target, lock)
        body.save(out/f'body-source-{i:02}.png')
        repaired.save(out/f'body-repaired-{i:02}.png')
        old, new = body.copy(), repaired.copy()
        old.alpha_composite(head)
        new.alpha_composite(translate_shared_layer(head, (0, bob)))
        old.save(out/f'before-{i:02}.png')
        new.save(out/f'after-{i:02}.png')
        before.append(_flatten(old)); after.append(_flatten(new))
        recipes.append({'frame': i, 'sourceLandmarks': source, 'targetLandmarks': target,
                        'lockY': lock, 'headTranslation': [0, bob]})
    for name, frames in [('before', before), ('after', after)]:
        frames[0].save(out/f'{name}.gif', save_all=True, append_images=frames[1:],
                       duration=durations, loop=0, disposal=2, optimize=False)
    sheet = Image.new('RGB', (4*width, 4*(height+20)), '#eef2f6')
    draw = ImageDraw.Draw(sheet)
    for i in range(len(before)):
        col, row = i % 4, (i//4)*2
        for offset, frames, label in [(0, before, 'before'), (1, after, 'after')]:
            x, y = col*width, (row+offset)*(height+20)
            sheet.paste(frames[i], (x, y))
            draw.text((x+5, y+height+3), f'{label} {i}', fill='#22354a')
    sheet.save(out/'before-after-sheet.png')
    # Separate original arm diagrams: both straight and bent row-centerline.
    arm = Image.new('RGBA', (120, 140))
    ad = ImageDraw.Draw(arm)
    ad.rectangle((42, 18, 54, 85), fill='#2c95a0', outline='#22354a')
    ad.rectangle((39, 86, 57, 104), fill='#e5b866', outline='#22354a')
    shaft_settings = {'start': [48, 18], 'wrist': [48, 86], 'length_scale': 1.25,
                      'width_scale': 1.15, 'target_start': [48, 18], 'rotation_radians': 0.0}
    mapped = shaft_hand_mapping(**shaft_settings)
    # Render geometric polygons from mapped vertices. This is not a generic
    # forward raster sampler and makes no claim of source texture preservation.
    elongated = Image.new('RGBA', arm.size)
    ed = ImageDraw.Draw(elongated)
    for poly, color in [([(42, 18), (54, 18), (54, 52), (54, 86), (42, 86), (42, 52)], '#2c95a0'),
                        ([(39, 86), (57, 86), (57, 104), (39, 104)], '#e5b866')]:
        ed.polygon([tuple(v) for v in mapped(poly)], fill=color, outline='#22354a')
    centers = [48+9*math.sin(max(0, y-18)/100) for y in range(140)]
    curved = Image.new('RGBA', arm.size)
    cd = ImageDraw.Draw(curved)
    for y in range(18, 106):
        center = round(centers[y]); cd.line((center-6, y, center+6, y), fill='#2c95a0')
    wider = widen_rows(curved, centers, root_y=25, blend_end_y=55, width_scale=1.45)
    for name, im in [('arm-source', arm), ('arm-extended', elongated),
                     ('width-source', curved), ('width-repaired', wider)]:
        im.save(out/f'{name}.png')
    arm_sheet = Image.new('RGB', (480, 162), '#eef2f6')
    for i, (im, name) in enumerate([(arm, 'shaft before'), (elongated, 'shaft after'),
                                  (curved, 'width before'), (wider, 'width after')]):
        arm_sheet.paste(_flatten(im), (i*120, 0))
        ImageDraw.Draw(arm_sheet).text((i*120+3, 143), name, fill='#22354a')
    arm_sheet.save(out/'arm-repairs.png')
    recipe = {'schema': 'dash-registration-fixture/1', 'canvas': [width, height],
              'timing': timeline, 'registration': recipes, 'shaft': shaft_settings,
              'width': {'centerlineX': centers, 'rootY': 25, 'blendEndY': 55, 'widthScale': 1.45},
              'resampling': 'Pillow BICUBIC one-row inverse mesh',
              'provenance': 'Original code-native geometric primitives; no imported art, model output, or character calibration.',
              'limitations': ['Not a gait, anatomy or unseen-character quality test.',
                              'Shaft example redraws mapped geometric polygons, not textured raster art.',
                              'Temporal playback observation BLOCKED / UNREVIEWED.'],
              'quality': {'visualApproval': False, 'temporalCertification': 'BLOCKED / UNREVIEWED'}}
    (out/'recipe.json').write_text(json.dumps(recipe, indent=2)+'\n')
    files = sorted(p for p in out.iterdir() if p.is_file())
    manifest = {'schema': 'dash-registration-manifest/1', 'generator': 'dash_registration.py --demo OUTPUT',
                'versions': {'numpy': np.__version__, 'Pillow': PILLOW_VERSION},
                'durationMs': timeline['durationMs'], 'frameCount': len(after),
                'protectedRowsExact': all(np.array_equal(np.asarray(Image.open(out/f'body-source-{i:02}.png'))[lock:],
                                                         np.asarray(Image.open(out/f'body-repaired-{i:02}.png'))[lock:]) for i in range(len(after))),
                'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', metavar='NEW_DIRECTORY', required=True)
    args = parser.parse_args(argv)
    manifest = build_demo(args.demo)
    print(json.dumps({'output': str(args.demo), 'frames': manifest['frameCount'],
                      'durationMs': manifest['durationMs'],
                      'quality': 'algorithm fixture; temporal certification BLOCKED / UNREVIEWED'}))


if __name__ == '__main__':
    main()
