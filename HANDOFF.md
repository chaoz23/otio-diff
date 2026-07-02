# otio-diff — Handoff Brief (historical)

> **Note:** this is the original agent-to-agent handoff brief the project was
> built from, kept for design rationale and provenance. The open items below
> are DONE — including a revision of locked decision #2 (identity key), forced
> by a concrete failing case; see `clip_key()` in `otio_diff.py` and
> `validation/README.md` for the real-file gate results.

**For the downstream agent completing this project.** The hard reasoning is done
and encoded in `otio_diff.py`. Your job is to finish the marked `# TODO(handoff):`
items, test, and ship. Do not re-open the locked design decisions (listed in the
module docstring) without a concrete failing case that forces it.

> **Starting state (verified, not assumed).** The full acceptance suite
> (`test_otio_diff.py`, 8 tests) **passes on the current scaffold** —
> confirmed by running it against `opentimelineio==0.18.1`. That includes the
> nested-stack flatten and the duplicate-clip multiset cases, which earlier
> drafts of this brief wrongly flagged as unfinished/ship-blocking. They work.
> The scaffold is more complete than its own inline TODO comments claim; the
> corrections below are the real remaining surface. Trust the green suite as your
> baseline, but see "Before you ship" for why green-on-synthetic-fixtures is
> necessary-but-not-sufficient.

## What this is
A structural editorial diff between two timelines — "what clips were added,
removed, retimed, or reordered between cut A and cut B." Rides OpenTimelineIO
(ASWF project, stable schema, multi-format parsing for free). Ships as a CLI plus
a thin MCP wrapper.

## What's already decided (locked — see docstring for rationale)
1. Match-then-classify, not positional diff.
2. Identity key = (media target_url, source_range start, source_range duration).
3. Scope = structural editorial only (clips/timing/order). Effects, transitions,
   retime curves are explicitly OUT — they don't round-trip across formats and
   are the maintenance sink to avoid.
4. Multi-format parsing comes free from OTIO adapters; write no parsers.

## What you need to finish (the real remaining surface)

Verified-working already (do NOT chase these — the tests prove them):
- ✅ `flatten_timeline` recursion into nested Stack/Track — works
  (`test_nested_stack_flattens` passes).
- ✅ Duplicate-clip handling — the surplus-pairing in `diff()` already produces
  the correct multiset result (`test_duplicate_clip_multiset` passes: `A A B`
  vs `A B C` → one A added, C removed). This was mislabeled a ship-blocker in an
  earlier draft; it is not.
- ✅ Missing media reference doesn't crash (`test_missing_available_range...` passes).

Genuinely open (polish, not correctness blockers):
1. **Frame-accurate human output** — convert seconds→frames using clip rate for
   editor-friendly detail ("SHOT_040 shortened by 12 frames"). Currently
   summary-only.
2. **Collection handling in `load`** — some adapters return a
   `SerializableCollection`, not a `Timeline`. Decide: first Timeline, or
   element-wise. Won't surface until you feed it a real multi-timeline export.
3. **Rate-aware rounding in `clip_key`** — ONLY if real AAF↔FCPXML exports show
   false mismatches from sub-frame float drift. Do not pre-optimize; wait for a
   failing real-file case.
4. **Retime semantics confirmation** — `test_retimed` currently passes, but
   confirm the behavior matches editor intent on a real shortened-clip export
   (see the note in that test). This is a "verify against reality," not a "build."
5. **MCP SDK import path** — confirm `from mcp.server.fastmcp import FastMCP`
   against your pinned `mcp` version; adjust if the SDK surface moved.

## Acceptance criteria (v1 is done when)

Already met on the scaffold (synthetic in-memory fixtures — all 8 tests green):
- ✅ added / removed / retimed / moved classified correctly on single-track cuts.
- ✅ Duplicate-clip timelines count correctly (multiset).
- ✅ Nested-stack timelines flatten correctly.
- ✅ Missing available_range doesn't crash.
- ✅ `--json` emits stable-shaped JSON.

Still required for ship:
- Mixed-format run on **real exports** (`a.edl b.fcpxml` from an actual NLE)
  produces a correct summary — see "Before you ship."
- Frame-accurate human detail lines implemented.
- README worked example; `opentimelineio` pinned to the exact tested version in
  `requirements.txt` and `pyproject.toml`.

## Before you ship (the necessary real-world gate)

The 8 passing tests are all **synthetic in-memory fixtures**. Green here proves
the diff logic is internally correct, but it CANNOT surface adapter quirks —
float drift between AAF and FCPXML, collection-return shapes, sub-frame rounding.
Those only appear with real files. So the one non-optional manual step before
release: export the *same cut with one known change* from Resolve or Premiere as
both `.edl` and `.fcpxml`, diff them, and confirm the reported change matches what
you actually did. That single real-file check is worth more than any number of
additional synthetic fixtures, and it's where TODOs #2 and #3 above will either
prove unnecessary or reveal themselves as needed.

## MCP wrapper (second deliverable, ~30 lines)
One tool, thin shell over the engine:

    diff_timelines(path_a: str, path_b: str) -> dict
      # calls load() + diff(), returns asdict(result)

Use the Python MCP SDK. stdio transport. No state, no config. The engine already
returns JSON-serializable dataclasses, so the wrapper is a pure adapter.

## Distribution / adoption (why this gets used)
- Passes both adoption gates: an agent cannot get "what changed between two cuts"
  from ffmpeg or a shell (decisive brute-force margin), and it rides OTIO's ASWF
  distribution.
- Two publish paths, do both: (a) standalone repo `otio-diff` with the MCP
  wrapper; (b) candidate PR into OpenTimelineIO's `examples/` or contrib — note
  their docs already list "Shots Added or Removed From The Cut" and "Conform New
  Renders Into The Cut" as first-class use cases, so a cut-diff example is
  squarely in-scope for upstream and likely welcomed.

## Maintenance contract
Pin opentimelineio. Core schema is stable and versioned. Budget: ~one touch/year
on version bump. If you find yourself editing this monthly, something has drifted
into the out-of-scope effects/transition territory — pull back.

## Guardrail
If tempted to add effects/transition/retime-curve diffing: don't. That's the
documented rabbit hole (proprietary per-tool serialization, no reliable
round-trip). The stable universal subset — clips, timing, order — is the entire
value proposition and the entire reason the maintenance stays near zero.
