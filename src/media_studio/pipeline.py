"""Bounded job lifecycle; no automatic resubmission of expensive GPU jobs."""
import json
import math
from pathlib import Path
import time
from .providers import Backend
from .workflow import digest


def save_manifest(path: Path, data: dict) -> None:
    partial = path.with_suffix(".tmp")
    partial.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    partial.replace(path)


def run(graph: dict, backend: Backend, out: Path, timeout: float = 2700, poll: float = 5,
        clock=time.monotonic, sleep=time.sleep) -> dict:
    if not math.isfinite(timeout) or not math.isfinite(poll) or timeout <= 0 or poll <= 0:
        raise ValueError("Timeout and polling interval must be positive finite numbers")
    # Exclusive directory creation prevents accidentally overwriting a prior run.
    out.mkdir(parents=True, exist_ok=False)
    graph_path = out / "workflow.json"
    graph_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    manifest = {"status": "submitting", "workflow_sha256": digest(graph_path),
                "artifacts": [], "human_review": "required", "timing_kind": "client_wall_seconds_including_queue"}
    manifest_path = out / "manifest.json"
    started = clock()
    try:
        save_manifest(manifest_path, manifest)
        job = backend.submit(graph)
        manifest.update(job_id=job, status="running")
        save_manifest(manifest_path, manifest)
        while clock() - started < timeout:
            record = backend.history(job)
            status = record.get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError("ComfyUI reported an execution error; inspect its local history")
            if status.get("completed") is True:
                files = []
                for node in record.get("outputs", {}).values():
                    for key in ("videos", "gifs", "images"):
                        for item in node.get(key, []):
                            if item.get("type") == "output" and str(item.get("filename", "")).lower().endswith(".mp4"):
                                if item not in files:
                                    files.append(item)
                if not files:
                    raise RuntimeError("Completed job has no MP4 output")
                for index, item in enumerate(files, 1):
                    # Never use server-supplied filenames as local paths.
                    target = out / f"clip-{index:02d}.mp4"
                    backend.download(item, target)
                    manifest["artifacts"].append({"file": target.name, "sha256": digest(target), "bytes": target.stat().st_size})
                manifest.update(status="completed", wall_seconds=round(clock() - started, 3))
                save_manifest(manifest_path, manifest)
                return manifest
            sleep(min(poll, max(0, timeout - (clock() - started))))
        raise TimeoutError("Local wait expired; the server job may still be running. Inspect it before resubmitting.")
    except Exception as error:
        manifest.update(status="failed", error_type=type(error).__name__, wall_seconds=round(clock() - started, 3))
        save_manifest(manifest_path, manifest)
        raise
