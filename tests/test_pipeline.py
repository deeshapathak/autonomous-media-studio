import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from media_studio.pipeline import run
from media_studio.providers import ComfyUI
from media_studio.workflow import prepare, read_graph

ROOT = Path(__file__).resolve().parents[1]
GRAPH = read_graph(ROOT / "examples/environment/workflow.json")


class FakeBackend:
    def __init__(self, records):
        self.records = iter(records)
        self.submissions = 0
        self.downloads = []

    def submit(self, graph):
        self.submissions += 1
        return "test-job"

    def history(self, job):
        return next(self.records, {})

    def download(self, artifact, target):
        self.downloads.append(target)
        target.write_bytes(b"test-only bytes; not media")


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def sleep(self, amount):
        self.now += amount


def completed(filename="render.mp4"):
    return {"status": {"completed": True, "status_str": "success"},
            "outputs": {"14": {"videos": [{"filename": filename, "type": "output", "subfolder": ""}]}}}


class LifecycleTests(unittest.TestCase):
    def invoke(self, backend, **kwargs):
        clock = Clock()
        return run(prepare(GRAPH), backend, self.out, timeout=10, poll=1, clock=clock, sleep=clock.sleep, **kwargs)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "run"

    def test_success_waits_for_completion_and_collects_hash(self):
        early = completed()
        early["status"]["completed"] = False
        backend = FakeBackend([early, completed("../../escape.mp4")])
        result = self.invoke(backend)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["wall_seconds"], 1)
        self.assertEqual(backend.downloads, [self.out / "clip-01.mp4"])
        self.assertEqual(len(result["artifacts"][0]["sha256"]), 64)
        self.assertEqual(json.loads((self.out / "manifest.json").read_text()), result)

    def test_timeout_records_job_without_resubmitting(self):
        backend = FakeBackend([])
        with self.assertRaises(TimeoutError):
            self.invoke(backend)
        self.assertEqual(backend.submissions, 1)
        data = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(data["job_id"], "test-job")
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error_type"], "TimeoutError")

    def test_execution_error_fails_without_download(self):
        backend = FakeBackend([{"status": {"status_str": "error"}}])
        with self.assertRaises(RuntimeError):
            self.invoke(backend)
        self.assertEqual(backend.downloads, [])

    def test_empty_completed_output_fails(self):
        backend = FakeBackend([{"status": {"completed": True}, "outputs": {}}])
        with self.assertRaisesRegex(RuntimeError, "no MP4"):
            self.invoke(backend)

    def test_download_error_preserves_failed_manifest(self):
        backend = FakeBackend([completed()])
        with patch.object(backend, "download", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.invoke(backend)
        self.assertEqual(json.loads((self.out / "manifest.json").read_text())["status"], "failed")

    def test_existing_directory_never_submits(self):
        self.out.mkdir()
        backend = FakeBackend([])
        with self.assertRaises(FileExistsError):
            self.invoke(backend)
        self.assertEqual(backend.submissions, 0)


class ContractTests(unittest.TestCase):
    def test_override_isolated_from_original(self):
        changed = prepare(GRAPH, seed=42, prompt="A quiet courtyard")
        self.assertNotIn("_vianca_bindings", changed)
        self.assertEqual(changed["6"]["inputs"]["noise_seed"], 42)
        self.assertEqual(GRAPH["6"]["inputs"]["noise_seed"], 170911)

    def test_invalid_seed_and_dangling_reference(self):
        for seed in (-1, 2**64, True):
            with self.assertRaises(ValueError):
                prepare(GRAPH, seed=seed)
        with self.assertRaisesRegex(ValueError, "Dangling"):
            prepare({"1": {"class_type": "Example", "inputs": {"x": ["missing", 0]}}})

    def test_endpoint_restriction(self):
        for endpoint in ("https://example.com", "http://example.com", "http://user:secret@localhost:8188", "http://localhost:8188/path"):
            with self.assertRaises(ValueError):
                ComfyUI(endpoint)

    def test_preflight_fails_missing_classes_and_weights(self):
        backend = ComfyUI()
        with patch.object(backend, "_json", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "Missing ComfyUI"):
                backend.preflight(prepare(GRAPH))
        graph = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "missing.safetensors"}}}
        info = {"UNETLoader": {"input": {"required": {"unet_name": [["present.safetensors"]]}}}}
        with patch.object(backend, "_json", return_value=info):
            with self.assertRaisesRegex(RuntimeError, "Missing model"):
                backend.preflight(graph)

    def test_prompt_rejection_and_history_contract(self):
        backend = ComfyUI()
        with patch.object(backend, "_json", return_value={"node_errors": {"5": "bad"}}):
            with self.assertRaises(RuntimeError):
                backend.submit(prepare(GRAPH))
        with patch.object(backend, "_json", return_value={"job": completed()}):
            self.assertTrue(backend.history("job")["status"]["completed"])


if __name__ == "__main__":
    unittest.main()
