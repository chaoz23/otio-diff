"""
test_otio_diff.py — acceptance tests for otio-diff.

HANDOFF NOTE
============
These tests are the definition of "done" for v1. They are written to FAIL against
the scaffold and PASS once the TODO(handoff) items in otio_diff.py are completed.
Build to green.

The fixtures are generated in-memory (no binary files to commit) so the suite is
self-contained and adapter-independent. Each builds a Timeline programmatically,
which also documents exactly what each diff category means.

Run:  pytest test_otio_diff.py -v

Fixture map (baseline = three clips A,B,C on one track):
  baseline          A B C
  added             A B C D      -> 1 added
  removed           A C          -> 1 removed
  retimed           A B' C       -> 1 retimed (B shortened)
  moved             A C B        -> reorder (B and C swap positions)
  duplicate         A A B        -> exercises multiset pairing (SHIP-BLOCKER)
  nested            A [B] C       -> B inside a nested Stack; must flatten
"""

import opentimelineio as otio
import pytest

from otio_diff import flatten_timeline, diff, load  # noqa: F401


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _clip(name: str, url: str, start: float, dur: float, rate: float = 24.0):
    """A clip with an ExternalReference and a source_range."""
    mr = otio.schema.ExternalReference(
        target_url=url,
        available_range=otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(0, rate),
            duration=otio.opentime.RationalTime(dur * 10, rate),  # generous avail
        ),
    )
    return otio.schema.Clip(
        name=name,
        media_reference=mr,
        source_range=otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(start, rate),
            duration=otio.opentime.RationalTime(dur, rate),
        ),
    )


def _timeline(clips, name="t"):
    tl = otio.schema.Timeline(name=name)
    track = otio.schema.Track(name="V1")
    for c in clips:
        track.append(c)
    tl.tracks.append(track)
    return tl


# Canonical media URLs — identity is (url, src_start, src_dur), NOT name.
A = ("file:///A.mov", 0.0, 48.0)
B = ("file:///B.mov", 0.0, 48.0)
C = ("file:///C.mov", 0.0, 48.0)


def baseline():
    return _timeline([_clip("A", *A), _clip("B", *B), _clip("C", *C)])


# ---------------------------------------------------------------------------
# Tests — one per diff category, building to green.
# ---------------------------------------------------------------------------

def test_identical_is_no_change():
    d = diff(flatten_timeline(baseline()), flatten_timeline(baseline()))
    assert not d.added and not d.removed and not d.retimed and not d.moved
    assert not d.shifted
    assert d.unchanged_count == 3


def test_added():
    D = ("file:///D.mov", 0.0, 48.0)
    revised = _timeline([_clip("A", *A), _clip("B", *B), _clip("C", *C), _clip("D", *D)])
    d = diff(flatten_timeline(baseline()), flatten_timeline(revised))
    assert len(d.added) == 1
    assert d.added[0]["media_url"] == "file:///D.mov"
    assert not d.removed


def test_removed():
    revised = _timeline([_clip("A", *A), _clip("C", *C)])  # B gone
    d = diff(flatten_timeline(baseline()), flatten_timeline(revised))
    assert len(d.removed) == 1
    assert d.removed[0]["media_url"] == "file:///B.mov"
    assert not d.added


def test_retimed():
    # B shortened from 48f to 36f (same media, same in-point, shorter duration).
    # RESOLVED (2026-07-02): identity key is (url, src_start); duration is a
    # compared attribute, so B reads as retimed. C slides earlier as the knock-on
    # ripple and reads as "shifted", NOT retimed — that separation is the point.
    # (The earlier version of this test passed vacuously: B fell out of its own
    # identity as removed+added, and the lone "retimed" entry was actually C.)
    B_short = ("file:///B.mov", 0.0, 36.0)
    revised = _timeline([_clip("A", *A), _clip("B", *B_short), _clip("C", *C)])
    d = diff(flatten_timeline(baseline()), flatten_timeline(revised))
    assert not d.added and not d.removed, (
        "a trimmed clip must not read as add/remove — duration is an attribute, "
        "not identity"
    )
    assert len(d.retimed) == 1
    assert d.retimed[0]["before"]["media_url"] == "file:///B.mov"
    assert len(d.shifted) == 1, "C slid earlier — should be shifted, not retimed"
    assert d.shifted[0]["before"]["media_url"] == "file:///C.mov"
    assert d.unchanged_count == 1  # A


def test_moved_reorder():
    revised = _timeline([_clip("A", *A), _clip("C", *C), _clip("B", *B)])  # B/C swap
    d = diff(flatten_timeline(baseline()), flatten_timeline(revised))
    assert d.moved, "reorder should populate moved"
    assert not d.added and not d.removed and not d.retimed
    assert not d.shifted, "moved subsumes the position change — no shifted noise"


def test_duplicate_clip_multiset():
    """
    Multiset pairing. Baseline A B C ; revised A A B  (C removed, extra A added).
    Correct result:
      - one A is unchanged/matched
      - one A is added
      - C is removed
    (Historical note: an earlier handoff draft flagged this as a ship-blocker;
    the multiset pairing in diff() handles it.)
    """
    revised = _timeline([_clip("A", *A), _clip("A", *A), _clip("B", *B)])
    d = diff(flatten_timeline(baseline()), flatten_timeline(revised))
    assert len(d.added) == 1 and d.added[0]["media_url"] == "file:///A.mov"
    assert len(d.removed) == 1 and d.removed[0]["media_url"] == "file:///C.mov"


def test_nested_stack_flattens():
    """B lives inside a nested Stack; flatten must still find all three clips."""
    inner = otio.schema.Stack(name="nested")
    inner_track = otio.schema.Track()
    inner_track.append(_clip("B", *B))
    inner.append(inner_track)

    tl = otio.schema.Timeline(name="nested_tl")
    track = otio.schema.Track(name="V1")
    track.append(_clip("A", *A))
    track.append(inner)
    track.append(_clip("C", *C))
    tl.tracks.append(track)

    recs = flatten_timeline(tl)
    urls = sorted(r.media_url for r in recs)
    assert urls == ["file:///A.mov", "file:///B.mov", "file:///C.mov"], (
        "nested clip B was not flattened — complete the recursion TODO"
    )


def test_missing_available_range_does_not_crash():
    """Clip with source_range but a MissingReference must not raise."""
    clip = otio.schema.Clip(
        name="X",
        media_reference=otio.schema.MissingReference(),
        source_range=otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(0, 24),
            duration=otio.opentime.RationalTime(24, 24),
        ),
    )
    tl = _timeline([clip])
    recs = flatten_timeline(tl)  # should not raise
    assert recs[0].media_url is None
