from __future__ import annotations

"""Helpers for generating pipeline prompt snippets."""

from typing import Any, Dict, List

from pipelines.loader import load_manifest

PIPELINE_PROMPT_SNIPPET: str = ""


def build_pipeline_prompt(manifest: List[Dict[str, Any]]) -> str:
    """Return YAML snippet documenting available pipelines."""
    if not manifest:
        return ""
    lines = ["## Available Pipelines"]
    for entry in manifest:
        pipe_id = entry.get("id")
        name = entry.get("name")
        lines.append(f"- id: {pipe_id}")
        if name:
            lines.append(f"  name: {name}")
        lines.append("  call_via: run_pipeline")
    return "\n".join(lines)


def init_pipeline_prompt() -> None:
    """Load manifest and prepare pipeline prompt snippet."""
    global PIPELINE_PROMPT_SNIPPET
    manifest = load_manifest()
    PIPELINE_PROMPT_SNIPPET = build_pipeline_prompt(manifest)
