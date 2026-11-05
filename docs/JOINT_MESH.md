# v0.7 mesh and coupled motion

Original implementation. No old rigs, pretrained code or remote model is used by this application. NumPy supplies array operations only.

A parent/child limb is composited in neutral source space and sampled through a6px triangle grid. A smooth longitudinal blend interpolates the two bone rotations (shortest angle), rather than averaging transform matrices. Source pixels are sampled with premultiplied-alpha bilinear interpolation. This avoids separately rotating painted caps and reduces linear-blend collapse, but does not guarantee volume conservation.

`jointMeshes` accepts only matching-side upper_arm/forearm and thigh/shin pairs; no duplicate/overlapping chains. Radius2..36px is manually calibrated; the blend zone is twice this radius. Large values can affect much of a short limb, so do not call this always a tiny joint patch. Existing cut lines/occluded shapes in the source remain artwork problems; a continuous confirmed texture is required. Inputs and original artwork remain untouched.

Per-frame diagnostics report occupied-alpha triangle inversion and minimum area ratio. Source-triangle bounding boxes containing alpha>.25 conservatively count as occupied. Inversion or strong compression is a warning even if bone lengths are fixed. Export adds meshCompressionWarning below area ratio.2; no automatic artistic approval. Empty source-space triangles may fold outside the drawn limb; all actual silhouettes must still be visually checked.

`coupled-v2` drives same-side wrist opposite actual leg reach via fixed-length arm IK; `armSwingScale` affects excursion. Upper/lower arms retain length. Wrist displacement is proportional to step reach instead of an independent cosine clock. A smooth bounded signal avoids hard-clamp wrist freezes; a small vertical pumping arc uses the same leg signal and its velocity, not an independent oscillator. Small opposite chest/hip rotations are planar stylization, not3D twist or mass dynamics. Arm and leg unreachable-target errors are separate diagnostics.

Known limitations: joint compression/contour bulging at strong bend, limited depth ordering, painted seams outside blend zone, no clothing physics or anatomy reconstruction. Wider gait and larger arms are not automatically better. Evaluate full cycles with original neutral proportions and true raster contact checks before selecting a candidate.


## v0.8 waist attachment
Optional `waistAttachment` has finite fractions0<=start<end<=1 and requires both thigh/shin meshes. Source points above start follow the existing torso affine; a smooth rotational correction transitions to the original leg mesh by end. No enlarged torso, fill patch, new pixels or silhouette inflation is used at neutral. Runtime source-pixel locations change deliberately during movement. This is a clothing/hip binding correction, not a3D pelvis model. The chosen transition can span most of a short thigh; check cuff, crotch, inner-thigh compression and source-neutral invariance. Some character/preset combinations still need authored garment layers.
