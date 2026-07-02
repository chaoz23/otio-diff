# Validation corpus

Real-file validation for the diff engine — files produced by actual NLEs, not
by this project's own writer (which would be circular).

## `wild/` — untouched NLE exports

Sample files from the OpenTimelineIO adapter test suites (Apache-2.0, same as
this project):

- EDLs from [otio-cmx3600-adapter](https://github.com/OpenTimelineIO/otio-cmx3600-adapter)
  `tests/sample_data/` — includes genuine Premiere, Avid, and Nucoda exports.
- FCPXMLs from [otio-fcpx-xml-adapter](https://github.com/OpenTimelineIO/otio-fcpx-xml-adapter)
  `tests/sample_data/` — real FCP X exports with compound clips, lanes,
  transitions, and markers.

## Known-change surgeries

"Cut B" files are made by editing the RAW native format by hand — a timecode
shifted in EDL text, a `duration` attribute changed in FCPXML — so the change
enters through the format itself, never through an OTIO writer:

- `cut_a.edl` = `wild/screening_example.edl` verbatim.
- `cut_b1_trim.edl` — event 003 out-point pulled 12 frames
  (`01:00:09:13 -> 01:00:09:01`, record out `00:59:58:00 -> 00:59:57:12`).
  Expected: `1 retimed (8 unchanged)`.
- `cut_b2_removed.edl` — event 005 (ZZ100_504B) deleted.
  Expected: `1 removed (8 unchanged)`.
- `fcpx_a.fcpxml` = `wild/fcpx_project.fcpxml` verbatim.
- `fcpx_b_trim.fcpxml` — top-level IMG_0268 asset-clip `duration="10s" ->
  "9.5s"` (15 frames @ 30fps). Expected: `1 retimed (30 unchanged)`.

This corpus caught two real bugs the synthetic suite could not: phantom moves
from gap insertion (fixed with relative-order/LIS move detection) and 25fps
EDLs failing to parse (fixed with `--rate`).
