"""
mcp_server.py — thin MCP wrapper over the otio-diff engine.

Second deliverable. Pure adapter: no state, no config, stdio transport. The engine
(otio_diff.py) already returns JSON-serializable dataclasses, so this file only
translates one MCP tool call into an engine call.

Run (once dependencies installed):
    python mcp_server.py
Register in an MCP client config as a stdio server pointing at this file.

Import path verified against mcp==1.28.1 (pinned in requirements.txt).
"""

from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from otio_diff import load, diff

mcp = FastMCP("otio-diff")


@mcp.tool()
def diff_timelines(path_a: str, path_b: str) -> dict:
    """
    Structural editorial diff between two timelines.

    Reads two timeline files (.otio/.edl/.fcpxml/.aaf — format auto-detected) and
    returns what changed: clips added, removed, retimed, or moved between them.

    Args:
        path_a: baseline timeline file path.
        path_b: revised timeline file path.

    Returns:
        dict with keys: added, removed, retimed, moved, unchanged_count.
        Each list holds clip records (name, media_url, source/timeline timing).
    """
    result = diff(load(path_a), load(path_b))
    return asdict(result)


if __name__ == "__main__":
    mcp.run()
