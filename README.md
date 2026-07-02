# otio-diff

Structural editorial diff between two timelines. Answers one question well:
**what changed between cut A and cut B** — which clips were added, removed,
retimed, or reordered.

Built on [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO),
so it reads `.otio`, `.edl`, `.fcpxml`, and `.aaf` with no per-format code — and
inherits OTIO's stable, versioned schema, which keeps maintenance near zero.

Works as a CLI and as an MCP tool for AI agents.

## Why this exists

An agent (or a person at a shell) can transcode, trim, and probe media with
ffmpeg all day. What neither can do from a shell is answer *"what did the editor
change between these two cuts"* — that requires reasoning over timeline structure,
which is exactly what OTIO models. This tool fills that gap and nothing else.

Deliberately **out of scope**: diffing effects, transitions, and retime curves.
Those serialize in proprietary, tool-specific ways and don't round-trip across
formats — chasing them is the maintenance sink this project exists to avoid. The
stable, universal subset (clips, timing, order) is the whole value.

## Install

```bash
pip install -e .            # CLI only
pip install -e ".[mcp]"     # CLI + MCP server
pip install -e ".[dev]"     # + pytest
```

## CLI usage

```bash
# same format
otio-diff baseline.otio revised.otio

# mixed formats — adapters auto-detect
otio-diff editors_cut.edl finishing.fcpxml

# machine-readable
otio-diff a.otio b.otio --json
```

Human output:

```
2 added, 1 removed, 1 retimed (14 unchanged)
```

JSON output (shape):

```json
{
  "added":   [ { "name": "...", "media_url": "...", "src_start": 0.0, ... } ],
  "removed": [ ... ],
  "retimed": [ { "key": [...], "before": {...}, "after": {...} } ],
  "moved":   [ ... ],
  "unchanged_count": 14
}
```

## MCP usage

Register `mcp_server.py` as a stdio MCP server in your client config. It exposes
one tool:

```
diff_timelines(path_a: str, path_b: str) -> dict
```

Then an agent can ask, e.g., *"diff the editor's cut against the finishing
timeline and tell me which shots were added overnight."*

## Real-world uses

- Conform / VFX pull-list changes: which shots entered or left the cut.
- Overnight-change review: what the editor touched since you last looked.
- Sanity-check a round-trip: what didn't survive an EDL/AAF export.

## How it works (one paragraph)

`read_from_file()` parses either input into OTIO's in-memory `Timeline`. The
engine flattens each to a list of clip records, then **matches clips by identity**
— `(media url, source in-point, duration)`, not timeline position, because
inserting one clip shifts every downstream timecode and would make a positional
diff report everything as changed. Matched clips are classified into
added / removed / retimed / moved.

## Maintenance contract

Pin `opentimelineio`. Its core schema is stable and versioned, so the expected
upkeep is roughly one version bump per year: bump, run `pytest`, ship. If you find
yourself editing monthly, something has drifted into the out-of-scope
effects/transition territory — pull it back out.

## Tests

```bash
pytest
```

The suite (`test_otio_diff.py`) builds fixtures in-memory and defines v1
acceptance. Notable cases: duplicate-clip timelines (multiset matching),
nested stacks (flattening), and missing media references (no crash).

## Status

v1 scaffold. See `HANDOFF.md` for the completed design decisions and the
remaining `TODO(handoff)` items. Build the tests to green.

## License

Apache-2.0 (matches OpenTimelineIO, to keep an upstream `examples/` contribution
frictionless).
