"""Explicit tools callable by an agent; no LLM or autonomous posting is bundled."""
from pathlib import Path
from .providers import ComfyUI
from .pipeline import run
from .workflow import prepare, read_graph


def plan_render(workflow: str, seed: int | None = None, prompt: str | None = None) -> dict:
    """Compile a generation request without contacting a model or allocating GPU memory."""
    return prepare(read_graph(Path(workflow)), seed=seed, prompt=prompt)


def render_local(workflow: str, output_directory: str, endpoint: str = "http://127.0.0.1:8188",
                 seed: int | None = None, prompt: str | None = None, timeout: float = 2700) -> dict:
    """Submit one local render after checking required nodes and model selections."""
    graph = plan_render(workflow, seed, prompt)
    backend = ComfyUI(endpoint)
    backend.preflight(graph)
    return run(graph, backend, Path(output_directory), timeout=timeout)
