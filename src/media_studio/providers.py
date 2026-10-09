"""Small model backend contract and the observed local ComfyUI HTTP adapter."""
import json
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class Backend(Protocol):
    def submit(self, graph: dict) -> str: ...
    def history(self, job_id: str) -> dict: ...
    def download(self, artifact: dict, target: Path) -> None: ...


class ComfyUI:
    def __init__(self, endpoint: str = "http://127.0.0.1:8188", request_timeout: float = 30):
        parsed = urlsplit(endpoint)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("This showcase accepts local HTTP endpoints only")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("Use a bare local endpoint without credentials or a path")
        self.endpoint = endpoint.rstrip("/")
        self.request_timeout = request_timeout

    def _json(self, route: str, payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(self.endpoint + route, data=data, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=self.request_timeout) as response:
            return json.load(response)

    def preflight(self, graph: dict) -> dict:
        info = self._json("/object_info")
        missing = sorted({node["class_type"] for node in graph.values()} - set(info))
        if missing:
            raise RuntimeError("Missing ComfyUI node classes: " + ", ".join(missing))
        # Loader choices are exposed by ComfyUI. Check exact filenames when available.
        for node in graph.values():
            required = info[node["class_type"]].get("input", {}).get("required", {})
            for field in ("vae_name", "unet_name", "clip_name"):
                spec = required.get(field)
                if field in node["inputs"] and spec and isinstance(spec[0], list):
                    if node["inputs"][field] not in spec[0]:
                        raise RuntimeError(f"Missing model file for {node['class_type']}: {node['inputs'][field]}")
        return {"node_classes_available": True, "node_count": len(graph)}

    def submit(self, graph: dict) -> str:
        result = self._json("/prompt", {"prompt": graph})
        if result.get("node_errors") or not result.get("prompt_id"):
            raise RuntimeError("ComfyUI rejected the workflow")
        return str(result["prompt_id"])

    def history(self, job_id: str) -> dict:
        from urllib.parse import quote
        return self._json("/history/" + quote(job_id, safe="")).get(job_id, {})

    def download(self, artifact: dict, target: Path) -> None:
        query = urlencode({k: artifact.get(k, "") for k in ("filename", "subfolder", "type")})
        partial = target.with_suffix(target.suffix + ".part")
        try:
            with urlopen(self.endpoint + "/view?" + query, timeout=self.request_timeout) as response, partial.open("wb") as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
            if partial.stat().st_size == 0:
                raise RuntimeError("ComfyUI returned an empty artifact")
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
