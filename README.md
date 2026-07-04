# otio-diff

Structural editorial diff between two timelines. Answers one question well:
**what changed between cut A and cut B** — which clips were added, removed,
retimed, moved, or shifted.

Built on [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO),
so it reads any format an OTIO adapter can parse — and inherits OTIO's stable,
versioned schema, which keeps maintenance near zero.

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

Requires Python 3.9–3.13 (OTIO 0.18.1's file adapters break on 3.14).

```bash
pip install -e .            # CLI, .otio files only
pip install -e ".[mcp]"     # + MCP server
pip install -e ".[dev]"     # + pytest
```

`.otio` support is built in. Other formats come from OTIO adapter plugins —
install the ones you need:

```bash
pip install otio-cmx3600-adapter    # .edl
pip install otio-fcpx-xml-adapter   # .fcpxml (FCP X / Resolve)
pip install otio-aaf-adapter        # .aaf (Avid)
```

## CLI usage

```bash
# same format
otio-diff baseline.otio revised.otio

# mixed formats — adapters auto-detect by extension
otio-diff editors_cut.edl finishing.fcpxml

# machine-readable
otio-diff a.otio b.otio --json
```

Worked example — cut B has one clip trimmed by 12 frames:

```
$ otio-diff cut_a.edl cut_b.fcpxml
1 retimed, 1 shifted (1 unchanged)
  ~ B shortened by 12f (48f -> 36f)
  . C shifted 12f earlier
```

The five change categories:

| Category  | Meaning |
|-----------|---------|
| `added`   | clip in B, not in A |
| `removed` | clip in A, not in B |
| `retimed` | same clip, trimmed duration changed |
| `moved`   | same clip, different ordinal position (reorder) |
| `shifted` | same clip, only slid on the timeline — the ripple effect of an upstream edit, kept separate so one trim doesn't read as N retimes downstream |

JSON output (shape):

```json
{
  "added":   [ { "name": "...", "media_url": "...", "src_start": 0.0, "rate": 24.0, ... } ],
  "removed": [ ... ],
  "retimed": [ { "key": [...], "before": {...}, "after": {...} } ],
  "moved":   [ ... ],
  "shifted": [ ... ],
  "unchanged_count": 1
}
```

## For agents

- **Exit codes follow `diff(1)`**: `0` = no structural changes, `1` = changes
  found, `2` = could not read an input. Branch on the exit code without parsing.
- **`--json` is stable-shaped**: the six top-level keys above are always
  present, empty lists included. Times are float seconds; `rate` is the clip
  frame rate (multiply to get frames).
- **MCP server**: register `mcp_server.py` as a stdio server; it exposes one
  tool, `diff_timelines(path_a, path_b) -> dict`, returning the same shape as
  `--json`.
- Errors go to stderr; stdout is exclusively the diff result.

## MCP usage

Register `mcp_server.py` as a stdio MCP server in your client config:

```json
{ "otio-diff": { "command": "python", "args": ["/path/to/mcp_server.py"] } }
```

Then an agent can ask, e.g., *"diff the editor's cut against the finishing
timeline and tell me which shots were added overnight."*

## Real-world uses

- Conform / VFX pull-list changes: which shots entered or left the cut.
- Overnight-change review: what the editor touched since you last looked.
- Sanity-check a round-trip: what didn't survive an EDL/AAF export.

## How it works (one paragraph)

`read_from_file()` parses either input into OTIO's in-memory `Timeline`. The
engine flattens each to a list of clip records (recursing into nested stacks),
then **matches clips by identity** — `(media url, source in-point)`, not timeline
position, because inserting one clip shifts every downstream timecode and would
make a positional diff report everything as changed. Duration is compared as an
attribute after matching, so an out-point trim reads as *retimed* rather than
removed+added. Duplicate identities are paired as a multiset. Matched clips are
classified into added / removed / retimed / moved / shifted. When media is
offline and has no URL, the clip name is used as a fallback identity; unnamed
offline clips remain unmatched so an ambiguous pair cannot be reported as
unchanged.

## Maintenance contract

Pin `opentimelineio`. Its core schema is stable and versioned, so the expected
upkeep is roughly one version bump per year: bump, run `pytest`, ship. If you find
yourself editing monthly, something has drifted into the out-of-scope
effects/transition territory — pull it back out.

## Tests

```bash
pytest
```

The suite (`test_otio_diff.py`) builds fixtures in-memory and defines
acceptance. Notable cases: duplicate-clip timelines (multiset matching), nested
stacks (flattening), missing-media identity and ambiguity, collection-returning
adapters, exit codes, and frame-accurate output.

## License

Apache-2.0 (matches OpenTimelineIO, to keep an upstream `examples/` contribution
frictionless).
