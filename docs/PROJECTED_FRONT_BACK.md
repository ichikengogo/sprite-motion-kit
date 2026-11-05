# Experimental normalized front/back projection

`projected_walk.py` is the older, manually registered 2D projection route. It uses each view's own source, not a mirrored side. It requires the module's **384×384 canvas, centerX=192, neutralHeight=317 and ground=349 normalization**. These are implementation constraints, not universal anatomy or recommended proportions for every character. For arbitrary canvases and authored poses use the distinct layered/cel routes.

`projectedWalk.confirmed` and confirmed registered parts are required. The existing merged-source route rejects overlapping assigned visible source pixels. That restriction belongs to this route only: it does not establish a general zero-overlap goal, and animated sockets may require deliberately authored hidden surfaces in another route.

Screen-left/right slots must be mapped to physical identities explicitly. Front and back use opposite depth conventions; numeric opposed endpoints do not establish readable depicted opposition. Shoes can be shortened in screen space around toe-off, so this is not a rigid-shoe or reconstructed-sole model. Front/back dash is unsupported.

Optional parameters include `armFadeDepth` (20–40 pixels), `armAmplitude` (0–10), `armSpread` (0–4), depth stride (8–48), lift (0–18), depth projection (0.1–0.45), and `legInterpolation: "linear"`. Check validation in the module for the exact complete schema. Leaving opt-in settings absent retains legacy behavior. Parameter ranges are not artistic approval.

`rigidRegions` can protect up to four source-space accessory boxes above the hip. Boxes are `[x0,y0,x1,y1]`, at least 2 pixels wide/high, with `feather` 4–24 pixels. Their core follows uniform display scale and body translation, with smooth transition outside. Register the actual accessory and attachment; the helper does not generate hidden backgrounds or correct occlusion.

Inspect all keys and intermediate phases, actual source garment boundaries, both shoulders, wrist/hand depth cues, folds and complete loop playback. Existing source and pose validation does not mean the front/back artwork is ready for production. All exports remain draft.
