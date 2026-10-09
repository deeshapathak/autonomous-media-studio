"""Validate an API graph and make explicit, reproducible generation overrides."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def prepare(graph: dict, seed: int | None = None, prompt: str | None = None) -> dict:
    graph = deepcopy(graph)
    # The original local graph includes editor-only prompt binding metadata.
    graph = {key: value for key, value in graph.items() if not key.startswith("_")}
    if not graph:
        raise ValueError("Workflow contains no nodes")
    for node_id, node in graph.items():
        if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict) or not node.get("class_type"):
            raise ValueError(f"Malformed workflow node: {node_id}")
        for value in node["inputs"].values():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                if value[0] not in graph:
                    raise ValueError(f"Dangling node reference: {node_id} -> {value[0]}")
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**64:
            raise ValueError("Seed must be an unsigned 64-bit integer")
        nodes = [n for n in graph.values() if n["class_type"] == "RandomNoise"]
        if len(nodes) != 1:
            raise ValueError("Seed override requires exactly one RandomNoise node")
        nodes[0]["inputs"]["noise_seed"] = seed
    if prompt is not None:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be non-empty text")
        nodes = [n for n in graph.values() if n["class_type"] == "MiniMaxH3ImageToVideo"]
        if len(nodes) != 1:
            raise ValueError("Prompt override requires exactly one H3 conditioning node")
        nodes[0]["inputs"]["prompt"] = prompt
    return graph


def read_graph(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))
